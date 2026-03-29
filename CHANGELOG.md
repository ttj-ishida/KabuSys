CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。
リリース日はリポジトリの現状に基づいて推定しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-29
--------------------

Added
- パッケージの初期公開。
  - パッケージ名: kabusys、バージョン: 0.1.0
  - モジュール構成: data, research, ai, monitoring, strategy, execution（公開 API として __all__ に設定）
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート
    - インラインコメントの取り扱い（スペース直前の # をコメントとみなす等）
  - _load_env_file で既存 OS 環境変数を protected として保護する仕組みを追加。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト local）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH / SQLITE_PATH のデフォルトパス（data 以下）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ
- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp: ニュース記事をまとめて OpenAI に送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルに保存する score_news を実装。
    - タイムウィンドウ計算（JST 基準 -> UTC 変換）、記事集約、チャンク送信 (最大 20 銘柄/リクエスト)。
    - スコアのバリデーションと ±1.0 クリップ処理。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフを伴う再試行ロジック。
    - JSON mode（gpt-4o-mini + response_format）を前提にし、余分な前後テキストを含むレスポンスから JSON を復元する処理を実装。
    - テスト容易性のため _call_openai_api の差し替えを想定（unittest.mock.patch）。
  - regime_detector: ETF(1321) の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して market_regime テーブルへ日次で書き込む score_regime を実装。
    - ma200_ratio の計算（target_date 未満のデータのみを使用しルックアヘッドを防止）。
    - マクロ記事抽出（キーワードリスト）、LLM による macro_sentiment 評価、フェイルセーフ（API 失敗時は 0.0）やリトライ処理を実装。
    - 結果は冪等に DB へ書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダーの判定ユーティリティを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合は曜日ベースのフォールバック（平日を営業日）を採用。
    - calendar_update_job により J-Quants から差分取得 → 冪等保存（save_market_calendar 呼び出しを想定）を実装。バックフィルや健全性チェックを搭載。
  - pipeline / ETLResult:
    - ETLResult データクラスを公開し、ETL の取得数/保存数・品質問題・エラーを集約可能に。
    - ETL の差分取得、バックフィル、品質チェックの基本設計を実装する土台を用意。
  - jquants_client を介した外部 API 連携を想定した設計（差分フェッチ・idempotent 保存）。
- Research（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算（データ不足時は None を返す）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率の計算（データ不足時は None）。
    - calc_value: raw_financials から最新の eps/roe を取り込み PER・ROE を計算（EPS が 0 の場合は None）。
    - DuckDB 上で SQL とウィンドウ関数を使って高効率に計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン（LEAD を利用）。
    - calc_ic: スピアマンランク相関（Information Coefficient）をランク化して算出。
    - rank / factor_summary: ランク化ユーティリティと統計サマリー（count/mean/std/min/max/median）。
  - 研究用ユーティリティは標準ライブラリのみで依存を最小化。
- DuckDB をデフォルトな分析 DB として採用。多くの集計/ウィンドウ処理は DuckDB SQL で実装。

Changed
- 設定の既定値:
  - KABUSYS_API_BASE_URL のデフォルトを "http://localhost:18080/kabusapi" に設定（kabu station ローカルモードを想定）。
  - DUCKDB_PATH / SQLITE_PATH に対して data/ 以下の相対パスをデフォルトとする。
- OpenAI 関連:
  - gpt-4o-mini と JSON mode（response_format={"type": "json_object"}）を使用する標準プロンプトを採用。
  - LLM 呼び出しはニュース系モジュール間でプライベート実装を分離（モジュール結合を低減）。

Fixed / Robustness
- ルックアヘッドバイアス対策: 各モジュール（news_nlp, regime_detector, research 等）は datetime.today() / date.today() に依存せず、target_date 引数に基づいて処理する設計を徹底。
- DB 書き込みは冪等性を重視（DELETE → INSERT など）。部分失敗時に既存データを不必要に消さない工夫あり（ai_scores 書き込みでコードを限定する等）。
- OpenAI 呼び出しのエラー処理強化:
  - RateLimitError / APIConnectionError / APITimeoutError に対する指数バックオフ付きリトライ。
  - APIError の status_code を考慮した 5xx 再試行ロジック。
  - レスポンスパース失敗や予期しない構造は警告ログを出してフェイルセーフにフォールバック（スコア=0.0 やスキップ）。
- .env ファイル読み込みエラーは警告に落とし処理継続（テスト・運用での堅牢性向上）。

Security
- OS 環境変数を保護する protected set を用いた .env 上書きの制御。
- 必須のシークレット（OpenAI, Slack, J-Quants, kabu API パスワード等）は Settings のプロパティで明示的に要求し、未設定時は ValueError を発生させる（明示的な失敗で誤動作を防止）。

Testing / Extensibility
- OpenAI 呼び出し点（各モジュールの _call_openai_api）をテストで差し替え可能に実装。
- score_news / score_regime は api_key を引数で注入可能（テストで環境変数を汚さずに実行可能）。

Notes / Limitations
- 外部依存: DuckDB（ローカル DB）、OpenAI Python SDK（例外クラスを利用）および J-Quants クライアント（kabusys.data.jquants_client を想定）。これらの実行環境が必要。
- 一部機能は設計ドキュメント（StrategyModel.md, DataPlatform.md）に基づく実装の骨格であり、外部 API キー・DB スキーマ・jquants_client 実装が揃うことで動作する想定。
- PBR・配当利回りなどの一部バリューファクターは現バージョンでは未実装。

Acknowledgements
- 本リリースは自動売買/リサーチ基盤の最初の機能セットを提供します。今後のリリースでモニタリング・実行・戦略モジュールの充実や品質チェック・CI の追加を予定しています。