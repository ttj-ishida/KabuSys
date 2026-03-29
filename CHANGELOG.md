CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
著しいバージョンは semver を想定しています。

Unreleased
----------

- 今後の変更／未リリースの作業はここに記載します。

[0.1.0] - 2026-03-29
-------------------

初回リリース。パッケージ「kabusys」の基本的なデータプラットフォーム、研究用ユーティリティ、AI ベースのニュース解析・市場レジーム判定機能を実装しました。主な追加点と設計上の意図は以下のとおりです。

Added
- パッケージ基盤
  - パッケージメタ情報を追加 (kabusys.__version__ = "0.1.0")。
  - パッケージ公開 API を定義 (__all__ に data, strategy, execution, monitoring を含む)。
- 設定および環境変数ロード (kabusys.config)
  - .env ファイルおよび環境変数から設定値を読み込む自動ロードを実装。
  - プロジェクトルート検出ロジックを導入 (.git または pyproject.toml を基準)。これにより CWD に依存せずに .env を探索可能。
  - .env パーサー実装: export プレフィックス、クォート、エスケープ、コメント処理を考慮した堅牢なパース。
  - OS 環境変数を保護する protected モード、override フラグ、KABUSYS_DISABLE_AUTO_ENV_LOAD フラグで自動ロードの無効化が可能。
  - Settings クラスを提供し、アプリ固有の設定項目（J-Quants、kabu API、Slack、DB パス、環境フラグ、ログレベル等）をプロパティで取得可能。
  - 設定値のバリデーション（例: KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
- データプラットフォーム (kabusys.data)
  - calendar_management モジュール
    - market_calendar を用いた営業日判定・探索ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合の曜日ベースのフォールバックを実装。
    - JPX カレンダー差分取得バッチ job を実装 (calendar_update_job)。バックフィル、健全性チェックを含む。
  - pipeline / ETL
    - ETLResult データクラスを公開し、ETL の取得数・保存数・品質問題・エラー概要を表現可能に。
    - テーブル存在チェック、最大日付取得などのユーティリティ実装。
  - etl モジュールの公開インターフェース（ETLResult の再エクスポート）。
- 研究用ユーティリティ (kabusys.research)
  - factor_research: ファクター計算実装
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離(ma200_dev) を計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR (atr_pct)、平均売買代金 (avg_turnover)、出来高比率 (volume_ratio) を計算。
    - calc_value: raw_financials と prices_daily を組み合わせた PER / ROE の計算。
    - DuckDB のウィンドウ関数を活用し、営業日・窓長バッファを考慮した実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト: 1,5,21 営業日）の将来リターン計算を実装。ホライズンの妥当性検証あり。
    - calc_ic: スピアマン（ランク）相関による IC 計算（欠損・非有限値除外、少数レコード保護）。
    - rank / factor_summary: 順位化・統計サマリー計算のユーティリティを実装。
  - kabusys.data.stats の zscore_normalize を re-export（研究ワークフローで利用）。
- AI / ニュース解析 (kabusys.ai)
  - news_nlp モジュール (score_news)
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算する calc_news_window を実装。
    - raw_news + news_symbols から銘柄ごとに記事を集約し、1 銘柄あたり最大記事数・最大文字数でトリミングして OpenAI にバッチ送信。
    - バッチサイズ・リトライ（429、ネットワーク断、タイムアウト、5xx で指数バックオフ）を実装。
    - レスポンスの厳密なバリデーションと復元ロジック（JSON decode エラー時は {} の抽出を試みる）を実装。
    - スコアを ±1.0 にクリップし、ai_scores テーブルへ冪等的に書き込む（部分失敗時に他銘柄の既存スコアを保持）。
    - テスト容易性のため _call_openai_api を差し替え可能に。
  - regime_detector モジュール (score_regime)
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロ記事の LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロ記事フィルタ用キーワード群を実装、最大取得記事数は制限あり。
    - OpenAI 呼び出しに対するリトライ・フォールバック（失敗時は macro_sentiment = 0.0）を実装。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を採用。
    - モジュール間の結合を避けるため、OpenAI 呼び出しは news_nlp と独立実装。
- 共通実装
  - DuckDB を利用する想定で SQL と Python を組み合わせた実装を採用。
  - ルックアヘッドバイアス防止のため、各モジュールは datetime.today()/date.today() を直接参照せず、target_date を外部から注入する設計。
  - OpenAI クライアント利用時は api_key の注入（引数 or 環境変数 OPENAI_API_KEY）を必須化し、未設定時は ValueError を送出することで安全策を導入。
  - ロギングを広範に追加し、運用時のトラブルシュート性を向上。
  - DuckDB executemany の空リスト制約に対するガードを追加（空 params の場合には実行をスキップ）。

Fixed / Robustness
- .env パーサーの堅牢化
  - export プレフィックスやクォート内のバックスラッシュエスケープ、インラインコメント処理を正しく扱うよう実装。
- OpenAI レスポンスのパース耐性向上
  - JSON パース失敗時に最外の {} を抽出して再パースを試行するフォールバックを実装。
  - 不正なレスポンスや未知コード、数値でない score を安全に無視することで部分失敗を許容。
- DB トランザクションの安全性
  - INSERT 前に DELETE を行い、例外発生時は ROLLBACK を試みて失敗時に警告ログを出す挙動を追加。
- フェイルセーフのデフォルト
  - データ不足や API 障害時に中立値（ma200_ratio=1.0、macro_sentiment=0.0、処理スキップ等）を利用して処理継続できるようにした。

Security
- 環境変数の保護
  - OS 環境変数を protected として .env による上書きを防止する挙動を導入。
- API キー必須化
  - OpenAI API キーが未指定の場合は ValueError を発生させ、誤った公開呼び出しを防止。

Notes / Implementation decisions
- DuckDB と SQL ウィンドウ関数を活用し、パフォーマンスと互換性を両立する設計。
- 外部依存（OpenAI SDK、duckdb）を直接使用するため、テスト時は該当関数をモックして検証可能。
- 現時点ではモニタリング/実行（strategy/execution/monitoring）モジュールの公開シンボルを定義しているが、詳細実装は別途追加予定。

Contributors
- 実装はコードベースから推測して記載（自動生成・解析に基づくドキュメント）。実際の貢献者情報はソース管理のコミットログを参照してください。

---
注: 本 CHANGELOG は提供されたソースコードから機能・振る舞いを推測して作成しています。実際のリリースノートはリポジトリのコミット履歴・リリース計画に基づき調整してください。