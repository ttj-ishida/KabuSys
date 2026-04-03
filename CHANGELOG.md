# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに準拠します。  
このファイルはコードベース（初回リリース相当）の内容から推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-03

### Added
- 初期リリース（kabusys パッケージ）
  - パッケージ メタ情報
    - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。
  - 環境設定 / ロード機能
    - src/kabusys/config.py
      - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートの検出は .git または pyproject.toml に基づく）。
      - 読み込み順序: OS 環境 > .env.local（上書き）> .env（未設定のみ）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト向け）。
      - 行パースロジックは export 形式・クォート・エスケープ・インラインコメント等に対応。
      - 必須環境変数取得（_require）および Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY の使用想定など）。
      - システム環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション、および利便性プロパティ（is_live / is_paper / is_dev）。
  - AI モジュール（OpenAI を利用した NLP）
    - src/kabusys/ai/news_nlp.py
      - raw_news / news_symbols を入力にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini + JSON Mode）でセンチメント（-1.0〜1.0）を評価して ai_scores テーブルへ書き込む処理を実装。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算の util（calc_news_window）。
      - バッチ処理（最大 20 銘柄／コール）、1 銘柄あたりの記事数と文字数制限（トリム）、レスポンス検証ロジックを実装。
      - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで制御。失敗時はスキップして処理継続（フェイルセーフ）。
      - テスト容易性のため _call_openai_api を差し替え可能に設計。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321（日経225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等書き込みを行う。
      - マクロ記事の抽出（マクロキーワード）・OpenAI 呼び出し・合成ロジック・リトライ/フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
      - ルックアヘッドバイアス対策として内部で date.today() 等を参照せず、target_date ベースで処理。
  - Data / ETL / カレンダー管理
    - src/kabusys/data/calendar_management.py
      - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）を実装。
      - DB 登録値を優先し、未登録日は曜日ベースでフォールバックする一貫した挙動。
      - JPX カレンダーを J-Quants API から差分取得して保存する夜間バッチ（calendar_update_job）を実装。バックフィルと健全性チェックあり。
    - src/kabusys/data/pipeline.py / etl.py
      - ETL の結果を表す ETLResult データクラスを提供（取得件数、保存件数、品質問題、エラー等を集約）。
      - 差分更新、バックフィル、保存（jquants_client 経由で冪等保存）、品質チェックを行う設計方針の実装方針をドキュメント化（実装の骨組み）。
    - src/kabusys/data/__init__.py に ETLResult の再エクスポート（etl.py）。
    - jquants_client, quality などの外部モジュールを介した統合を想定。
  - Research（ファクター・特徴量探索）
    - src/kabusys/research/factor_research.py
      - モメンタム、ボラティリティ、バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）を実装。
      - DuckDB の SQL ウィンドウ関数を利用して効率的に計算。データ不足時は None を返す等の堅牢性を確保。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク化ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
      - pandas 等の外部依存を避け、標準ライブラリで実装。
    - src/kabusys/research/__init__.py で主要関数を公開。
  - その他ユーティリティ
    - 各所で DuckDB 接続を前提とした SQL 実装（prices_daily, raw_news, ai_scores, market_regime, raw_financials, market_calendar 等）を想定。
    - ログ出力と警告を多用し、失敗時のフォールバックや診断を容易にしている。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Deprecated
- なし

### Removed
- なし

### Security
- API キーの取り扱い
  - OpenAI API は呼び出し時に api_key 引数または環境変数 OPENAI_API_KEY を要求。未設定時は ValueError を発生させる仕様（明示的なエラーにより誤使用を防止）。
  - 環境変数ロード時、既存の OS 環境変数は protected として保護される（.env による上書きを防止）。
  - KABU_API_PASSWORD, JQUANTS_REFRESH_TOKEN 等の機密情報は環境変数で管理する想定。

### Notes / Design decisions / Migration
- ルックアヘッドバイアス対策
  - AI スコアリング／レジーム判定／ETL/Research の全てで内部で datetime.today() を参照せず、target_date ベースでウィンドウを計算する設計になっているため、バックテストと実運用で一貫した挙動を期待できる。
- フェイルセーフ挙動
  - OpenAI 呼び出し失敗時はスコアを 0.0 にフォールバックする等、外部依存の障害があっても処理全体を停止させない設計。
- テスト容易性
  - OpenAI 呼び出し部分（_call_openai_api）やクライアント作成部は差し替え可能に設計され、ユニットテストでモック可能。
- DuckDB との互換性注意
  - executemany に空リストを渡さない等、DuckDB のバージョン差異を考慮した実装がされている。
- ロギング
  - 各処理で詳細な INFO/DEBUG/WARNING ログを出力するため、運用時の監視・トラブルシュートが容易。

---

この CHANGELOG はソースコードから推測して記載しています。実際のリリースノートとして公開する場合は、リリース日・インパクトの高い変更点（Breaking changes）・既知の問題点などをプロジェクトの実運用情報に合わせて追記してください。