CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。  
このファイルはコードベースの現状（ソースコードの内容）から推測して作成したもので、実際のコミット履歴とは異なる可能性があります。

Unreleased
----------

- なし（初回リリースに向けて準備中の変更点・TODO をここに記載してください）

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。
    - __all__ に data, strategy, execution, monitoring を公開モジュールとして宣言（実際のサブモジュールは別ファイルで管理）。
- 設定管理:
  - src/kabusys/config.py
    - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
      - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を検索。
      - 読み込み順: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - .env パーサの実装:
      - コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いをサポート。
    - Settings クラスを提供し、アプリ設定をプロパティ経由で取得可能:
      - 必須値チェックを行う _require()（未設定時は ValueError）。
      - 提供プロパティ例: jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path（デフォルト data/kabusys.duckdb）, sqlite_path（デフォルト data/monitoring.db）, env, log_level, is_live, is_paper, is_dev。
      - env と log_level の値検証（許容値は内部定数で制御）。
- AI（自然言語処理）:
  - src/kabusys/ai/news_nlp.py
    - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント分析し、ai_scores テーブルへ書き込む機能（score_news）。
    - 処理の特徴:
      - JST ベースのニュース収集ウィンドウ（前日 15:00 ～ 当日 08:30 JST）を計算する calc_news_window。
      - raw_news / news_symbols から銘柄ごとに最新記事を集約し、1銘柄あたり最大記事数・最大文字数でトリム。
      - 最大 20 銘柄ずつバッチで API に送信（_BATCH_SIZE）。
      - 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
      - JSON Mode のレスポンス検証とスコアの ±1 でのクリップ。
      - 部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT による置換を行う（冪等性に配慮）。
    - テスト容易性: _call_openai_api を unittest.mock.patch で差し替え可能。
  - src/kabusys/ai/regime_detector.py
    - 市場レジーム（bull/neutral/bear）判定ロジック（score_regime）。
    - 判定ロジック:
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成してスコア化。
      - マクロニュースは news_nlp.calc_news_window を用いて記事を抽出し、OpenAI (gpt-4o-mini) を用いて JSON 出力で macro_sentiment を取得。
      - API エラーやパース失敗時は macro_sentiment = 0.0 としてフェイルセーフに継続。
      - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 再試行ロジック（リトライ・バックオフ）と 5xx の扱いを明確化。
- Data / ETL / カレンダー / パイプライン:
  - src/kabusys/data/pipeline.py
    - ETL パイプラインのフレームワーク（ETLResult データクラスの導入）。
    - 差分取得、バックフィル、品質チェック（quality モジュール使用）を想定した設計。
    - ETLResult により取得数・保存数・品質問題・エラー一覧を集約する仕組みを提供。has_errors / has_quality_errors / to_dict を備える。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult を再エクスポート。
  - src/kabusys/data/calendar_management.py
    - JPX 市場カレンダー管理と営業日判定ユーティリティを実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - market_calendar テーブルがない場合は曜日ベース（土日非営業日）でフォールバックする設計。
      - calendar_update_job により J-Quants API からの差分取得 → market_calendar へ冪等保存（バックフィル・健全性チェックあり）。
    - 最大探索日数・バックフィル日数・先読み範囲などの定数を設定し、安全機構を備える。
- Research（ファクター・解析）:
  - src/kabusys/research/factor_research.py
    - ファクター計算機能を実装:
      - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）。データ不足時は None を返す。
      - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率など。
      - calc_value: raw_financials から最新財務を取得して PER/ROE を計算（EPS=0/欠損は None）。
    - DuckDB を SQL とウィンドウ関数で効率的に処理。
  - src/kabusys/research/feature_exploration.py
    - 特徴量探索系ユーティリティ:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の検証あり。
      - calc_ic: スピアマンランク相関（IC）を計算。3件未満は None。
      - rank: 同順位（ties）を平均ランクにするランク化ユーティリティ。
      - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
- アセット: モジュール再エクスポート
  - src/kabusys/ai/__init__.py で score_news を公開。
  - src/kabusys/research/__init__.py で主要関数（calc_momentum 等）と zscore_normalize を公開。
  - src/kabusys/data/__init__.py は存在（パッケージ化のための空ファイル）。

Changed
- 初回リリースのため、内部 API 設計・関数シグネチャを整理。以降の互換性に注意して拡張を検討。

Fixed
- N/A（初回リリース）

Deprecated
- N/A

Removed
- N/A

Security
- OpenAI API キーや各種トークンは環境変数で管理する設計。
  - 必須環境変数（使用する機能に応じて）:
    - OPENAI_API_KEY（AI 機能: score_news / score_regime）
    - JQUANTS_REFRESH_TOKEN（データ取得）
    - KABU_API_PASSWORD（kabu ステーション API）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知）
  - 環境変数未設定時は Settings プロパティで ValueError を送出するか、AI モジュールで明確に検出してエラーを返す（呼び出し側での対処が必要）。
- .env 自動ロードはデフォルトで有効。テスト環境や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化を推奨。

Notes（設計上の重要点 / 既知の制約）
- DuckDB を利用する前提（DuckDB 接続オブジェクトを各関数に注入）。
  - 一部処理で executemany に空リストを渡さない等、DuckDB のバージョン依存挙動に配慮した実装がある。
- AI（OpenAI）呼び出しは JSON モードを期待し、レスポンスパース失敗時はフェイルセーフ（0.0 やスキップ）で続行する設計。
- 時刻処理はルックアヘッドバイアスを防ぐため、datetime.today() や date.today() を参照しない実装方針が採られている（target_date を呼び出し側から渡す）。
- テスト容易性のため、OpenAI 呼び出し用の内部関数（_call_openai_api）を差し替えられるようにしている。
- 本リリースでは「発注・実行（execution）」「モニタリング（monitoring）」「戦略（strategy）」の実装詳細は提示ファイルからは確認できないため、これらは今後の拡張対象。

今後の改善案（推奨）
- AI 呼び出しの抽象化層を拡張して、別 LLM やローカル評価器を差し替え可能にすると柔軟性が向上。
- エンドツーエンドの統合テスト（DuckDB のインメモリ DB を使用）を追加して ETL → ファクター → リサーチ → AI スコアリングのパイプライン整合性を検証。
- セキュリティ: 機密情報管理（Vault 等）への移行オプションを検討。
- observability: 各ジョブのメトリクス（成功率、API レイテンシ、書き込み件数）を Prometheus 等へエクスポート。

お問い合わせ
- 本 CHANGELOG は提供されたソースコードから推測して作成したもので、実際のリリースノート作成時にはコミット単位の記録に基づく追記・修正を推奨します。