# CHANGELOG

すべての変更は Keep a Changelog の仕様に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注記:
- このリリースはコードベースから推測して作成した初期公開版の変更履歴です（パッケージバージョン: 0.1.0）。
- 実行にはいくつかの環境変数とデータベーステーブル（DuckDB）が必要です。下の「重要な注意点」を参照してください。

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリース: kabusys（日本株自動売買システム）を公開。
  - パッケージエントリポイント: src/kabusys/__init__.py（バージョン 0.1.0、公開サブパッケージ: data, research, ai 等を想定）
- 環境設定管理モジュール（src/kabusys/config.py）
  - .env/.env.local の自動読み込み（プロジェクトルートの検出は .git または pyproject.toml に基づく）。
  - .env 行パーサ（export 構文、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い対応）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスによる型付きプロパティ（J-Quants、kabuAPI、Slack、DBパス、環境判定、ログレベル等）。
  - 環境変数の必須チェックと値検証（KABUSYS_ENV, LOG_LEVEL の検証）。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとのテキストを作成。
    - OpenAI（gpt-4o-mini）を用いたバッチ評価（最大 20 銘柄/チャンク）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）の計算ユーティリティ。
    - レスポンス検証・JSON 復元処理、スコアの ±1.0 クリップ、部分失敗時のフェイルセーフ設計。
    - DuckDB の ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT の戦略）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成してレジーム判定（bull/neutral/bear）。
    - マクロキーワード抽出、OpenAI 呼び出し、リトライ/バックオフ、API エラー時は macro_sentiment=0.0 で継続。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
  - テスト容易性: OpenAI 呼び出し箇所は内部関数で分離され、ユニットテスト時にモック可能。

- Research（ファクター計算）モジュール（src/kabusys/research）
  - calc_momentum / calc_volatility / calc_value（src/kabusys/research/factor_research.py）
    - モメンタム・ボラティリティ・バリュー系の定量ファクター計算を DuckDB 上の prices_daily/raw_financials を参照して実装。
    - 200 日移動平均、ATR、出来高・出来高比率、PER/ROE 等を計算。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、rank/統計サマリー等。
    - pandas 等に依存せず標準ライブラリ＋DuckDBで実装。

- Data（データ基盤）モジュール（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を元にした営業日判定、次/前営業日取得、区間内営業日の列挙、SQ（特別清算日）判定。
    - DB 未取得時は曜日ベースでフォールバック。最大探索日数制限で無限ループ回避。
    - calendar_update_job: J-Quants から差分取得して冪等的に保存。バックフィルと健全性チェックを実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分取得、保存（jquants_client 経由で冪等保存）、品質チェックの統合ワークフローを設計。
    - ETLResult データクラス（保存件数・品質問題・エラー等の集約）を提供。
    - 最終取得日の自動計算、バックフィル、品質チェックの収集方針（Fail-Fast はしない）を実装。
  - etl モジュール経由での ETLResult の公開（src/kabusys/data/etl.py）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 外部 API キー（OpenAI 等）は引数注入または環境変数経由で明示的に解決する設計。デフォルトでコード内にハードコードしない方針。

### Notes / 実装上の重要な設計判断
- ルックアヘッドバイアス回避:
  - date.today() / datetime.today() に依存しない処理設計（target_date を引数化）。
  - DB クエリでは date < target_date など排他条件を利用。
- 冪等性:
  - ai_scores / market_regime / market_calendar への書き込みは既存行を削除してから挿入する、または ON CONFLICT 相当のロジックで上書きすることで冪等を確保。
- フェイルセーフ:
  - OpenAI API 呼び出しが失敗した場合、スコアはゼロや空スコアでフォールバックして処理を続行（例外を投げないパターンが基本）。
- ロバストなパース/バリデーション:
  - .env パーサや OpenAI レスポンスの JSON パースは堅牢に実装（余分な前後テキストの復元、数値チェック、未知コードの無視等）。
- テストしやすさ:
  - OpenAI 呼び出しなど外部依存は内部関数（_call_openai_api 等）で分離しているため、ユニットテストで差し替え可能。

### 既知の前提・必要な環境（運用時注意）
- 必須環境変数（実行時に最低限必要なもの）
  - OPENAI_API_KEY（AI モジュールを使用する場合）
  - JQUANTS_REFRESH_TOKEN（J-Quants API を利用する ETL 等）
  - KABU_API_PASSWORD（kabu ステーション API 利用）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知）
- DuckDB 上に以下のテーブル構造が存在することを前提:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等（各モジュールの SQL で参照）。
- デフォルトのデータベースパス:
  - duckdb: data/kabusys.duckdb（Settings.duckdb_path で変更可）
  - sqlite: data/monitoring.db（Settings.sqlite_path）
- 自動 .env 読み込みはプロジェクトルート検出に依存しているため、配布後は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用するか明示的に環境を設定すること。

### Breaking Changes
- なし（初期リリース）

---

将来的なリリースでは、以下の改善が想定されます（例）:
- AI モデルや API クライアントの抽象化（複数ベンダー対応、ローカルモデル対応）
- ETL の並列化や差分処理の細分化
- 監視/アラート用の監視モジュール（monitoring）や実行モジュール（execution）の実装拡充
- DB スキーマ定義（DDL）・マイグレーションスクリプトの同梱

もし特定ファイルごと、または追加の日付・変更点を反映したい場合は、その内容（コミットや変更差分）を提供してください。これを基にバージョン別の詳細な CHANGELOG を生成します。