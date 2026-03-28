# Changelog

すべての著名な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。日本株向けの自動売買 / データプラットフォーム構成を含むライブラリを公開。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys パッケージの __version__ を "0.1.0" に設定し、主要サブパッケージ（data, research, ai, ...）をエクスポートするように定義（src/kabusys/__init__.py）。
- 環境設定
  - 環境変数・設定管理モジュールを追加（src/kabusys/config.py）。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動検出して読み込む自動ロード機能（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env の行パースは export 形式、シングル/ダブルクォート、エスケープ、コメント処理などをサポート。
    - 読み込み時に OS 環境変数を保護するための protected キー概念（.env.local は override=True）。
    - 必須環境変数未設定時には _require() が ValueError を送出。
    - 設定アクセス用 Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境 / ログレベル等）。
    - KABUSYS_ENV と LOG_LEVEL の入力検証を実施（許可値セットを定義）。
- AI（自然言語処理）
  - ニュース NLP スコアリング機能（src/kabusys/ai/news_nlp.py）。
    - raw_news / news_symbols を集約し、銘柄ごとに前日15:00〜当日08:30(JST) の記事を結合して OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得。
    - バッチ処理（デフォルト 20 銘柄/コール）、1 銘柄あたり最大記事数・最大文字数でトリムする仕組みを提供。
    - レスポンスバリデーション（JSON 抽出、results 配列・スキーマ検証、未知コードの無視、スコアの数値性・有限性チェック）を実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実施。失敗時は該当チャンクをスキップし全体処理を継続（フェイルセーフ）。
    - DuckDB への書き込みは部分更新（DELETE → INSERT）で冪等性を確保、DuckDB executemany の空リスト制約に配慮。
    - 公開 API: score_news(conn, target_date, api_key=None)、および calc_news_window() を提供。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api で分離しモック可能。
  - 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）。
    - ETF 1321（225連動）200 日 MA 乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）の線形合成で市場レジーム（bull/neutral/bear）を日次判定。
    - prices_daily からの ma200 比率計算、raw_news からマクロキーワード抽出、OpenAI（gpt-4o-mini）によるマクロセンチメント推定、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API 呼び出しは最大リトライ回数・バックオフ制御、失敗時は macro_sentiment=0.0 として処理を継続するフェイルセーフ。
    - ルックアヘッドバイアス回避のため内部で datetime.today()/date.today() を参照せず、target_date 未満のデータのみを使用する方針を明示。
    - テスト容易性: OpenAI 呼び出しを _call_openai_api で分離しモック可能。
    - 公開 API: score_regime(conn, target_date, api_key=None)。
- データ関連（Data）
  - カレンダー管理モジュール（src/kabusys/data/calendar_management.py）。
    - market_calendar に基づく営業日判定(is_trading_day / is_sq_day)、前後の営業日取得(next_trading_day / prev_trading_day)、期間内営業日列挙(get_trading_days) を実装。
    - カレンダーデータ未取得時は曜日ベースでフォールバック（週末は非営業日）。
    - 夜間バッチ calendar_update_job() を実装: J-Quants からカレンダー差分を取得して冪等的に保存、バックフィルと健全性チェックを実施。
    - 最大探索日数やバックフィル・先読み等の安全パラメータを定義。
  - ETL パイプライン（src/kabusys/data/pipeline.py, etl.py）。
    - 差分更新、保存（jquants_client の save_* を利用して冪等保存）、品質チェック（quality モジュール）を想定した ETL ロジック骨格。
    - ETL 実行結果を表現する ETLResult データクラスを提供（target_date, fetched/saved カウント, quality_issues, errors 等。to_dict をサポート）。
    - 内部ユーティリティ: テーブル存在チェックや最大日付取得などのヘルパーを実装。
    - デフォルトのバックフィル日数、カレンダー先読み等の定数を定義。
  - jquants_client との連携を想定した設計（fetch/save の呼び出し場所を確保）。
- リサーチ / ファクター計算（src/kabusys/research/*）
  - ファクター計算モジュール（factor_research.py）。
    - Momentum（1M/3M/6M リターン、ma200 乖離）、Volatility（20 日 ATR、相対 ATR）、Liquidity（20 日平均売買代金・出来高比率）、Value（PER/ROE）を計算する関数を実装。
    - DuckDB のウィンドウ関数を活用し、価格・財務データ（prices_daily / raw_financials）から必要値を取得。
    - データ不足時は None を返すなど安全処理を実装。
    - 公開 API: calc_momentum(conn, target_date), calc_volatility(...), calc_value(...)
  - 特徴量探索モジュール（feature_exploration.py）。
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）を実装。horizons の検証あり。
    - Information Coefficient（Spearman の ρ）を計算する calc_ic() 実装。必要レコード数が不足する場合は None を返す。
    - ランキング（同順位は平均ランク）の rank() ユーティリティを実装。
    - ファクター統計 summary（count/mean/std/min/max/median）を計算する factor_summary() を実装。
- 互換性・実装上の配慮
  - DuckDB のバージョン差異（executemany の空リスト制約・リスト型バインドの不安定性）を考慮した実装。
  - LLM レスポンスの不整合（前後余計なテキスト）に対して JSON 抽出（最外の {} を探す）で復元する耐障害性。
  - 可能な限り外部副作用（外部 API 呼び出しや現在時刻参照）を明示的に引数化してテスト容易性・再現性を確保。
  - ロギング（logger）を各モジュールに配置し、警告・情報を詳細に出力する設計。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- OpenAI API キーと各種シークレットは Settings 経由で取得し、未設定時は明示的にエラーを出す（誤った無音フェイルを防ぐ）。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（score_news/score_regime 実行時）
- .env の自動読み込みはデフォルトで有効。CI / テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が適切に作成されている前提です。ETL / 保存処理は jquants_client 実装に依存します。

---

今後リリースでは以下を予定しています（例）:
- ETL 実行フローの具現化（jquants_client の具象実装・バッチ実行スクリプト）
- 監視・実行（execution / monitoring）モジュールの実装
- ドキュメント（API 参照・運用手順）と例題ノートの追加

（以上）