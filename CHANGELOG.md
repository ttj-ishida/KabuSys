CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは "Keep a Changelog" の慣習に準拠しています。  
バージョン番号は semver に従います。

[0.1.0] - 2026-03-29
--------------------

Added
- 初回公開リリース。パッケージ名: kabusys, バージョン 0.1.0。
- パッケージのエントリポイントを追加（src/kabusys/__init__.py）。
  - __all__ に data, strategy, execution, monitoring を公開。
- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local の自動読み込み機能を提供（プロジェクトルート検出: .git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - export KEY=val 形式、クォート済み値、インラインコメント処理などを考慮した .env パーサ実装。
  - 環境変数の保護（OS環境変数を protected セットとして扱い .env.local で上書き不可にする扱い）や上書きオプションを実装。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DBパス / 環境種別 / ログレベル等の取得とバリデーションを行う。
    - 必須キー取得時に未設定だと ValueError を送出する _require 実装。
    - KABUSYS_ENV, LOG_LEVEL の有効値チェックを実装。
- AI 関連モジュールを追加（src/kabusys/ai/*）。
  - ニュース NLP スコアリング（news_nlp.score_news）
    - OpenAI（gpt-4o-mini）を利用したニュース記事の銘柄別センチメント解析を実装。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）と DuckDB からの記事集約ロジックを実装。
    - バッチ処理（最大20銘柄/チャンク）、トークン肥大対策（記事数・文字数トリム）、レスポンスバリデーション、±1.0 クリップを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装。
    - ai_scores テーブルへの冪等的な差し替え（DELETE → INSERT）を行う。部分失敗時の既存データ保護ロジックあり。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等保存。
    - マクロ記事抽出（キーワードフィルタ）、LLM 呼び出し（gpt-4o-mini + JSON mode）、リトライ/フォールバック（API失敗時 macro_sentiment=0.0）を実装。
    - DuckDB を用いた ma200_ratio 計算や DB トランザクション（BEGIN/DELETE/INSERT/COMMIT）を実装。
- Research モジュールを追加（src/kabusys/research/*）。
  - factor_research: モメンタム、ボラティリティ、バリュー（per, roe）などのファクター計算関数を実装（DuckDB SQL ベース）。
  - feature_exploration: 将来リターン計算(calc_forward_returns)、IC（Spearman）計算(calc_ic)、ランク関数(rank)、統計サマリー(factor_summary) を実装。外部依存なし（標準ライブラリと DuckDB）。
  - 解析ユーティリティの再エクスポート（zscore_normalize など）。
- Data モジュールを追加（src/kabusys/data/*）。
  - calendar_management:
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar 未取得時は曜日ベースのフォールバックを行う設計。
    - calendar_update_job: J-Quants から差分取得して冪等保存、バックフィル・健全性チェックを含む夜間バッチジョブを実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の構造化、品質問題の集約、エラー判定ヘルパー）。
    - ETL の差分更新方針、品質チェック方針を反映したパイプライン骨子（jquants_client 経由の取得・保存・品質チェック連携）を実装。
  - jquants_client および quality モジュールとのインテグレーション用フックを用意（実実装は jquants_client 側に依存）。
- DuckDB を主要なデータ操作エンジンとして採用。SQL と Python の混成で高効率に集計・ウィンドウ関数を利用。
- テストしやすさのため、API 呼び出し箇所（OpenAI 呼び出しなど）を差し替えられる設計にしている点を明記。

Changed
- （初回リリースのため変更履歴はなし）

Fixed
- （初回リリースのため修正履歴はなし）

Security
- OpenAI / 外部 API キーは環境変数で管理。キー未設定時は明確な ValueError を発生させ、誤動作を防止。

Notes / Design decisions
- ルックアヘッドバイアス防止: いずれのモジュールも内部で datetime.today()/date.today() を安易に参照せず、target_date で明示的に評価する設計。
- フェイルセーフ: LLM/API の失敗はスコア計算において安全側のデフォルト（例: macro_sentiment=0.0）にフォールバックし、処理を継続する方針。
- 冪等性: DB 書き込みは可能な限り冪等に実装（DELETE → INSERT、ON CONFLICT 相当の保存）して再実行に耐える。
- DuckDB executemany の互換性配慮: 空リストを渡せない実装差異を考慮して空チェックを行う。
- ログと警告: 入力データ不足・APIエラー・ROLLBACK失敗など重要イベントでログ出力を行い運用時に原因追跡しやすくしている。

互換性 / 注意事項
- OpenAI の利用には OPENAI_API_KEY が必要（各関数は api_key 引数で上書き可能）。未設定時は ValueError。
- .env の自動読み込みはパッケージ配布後も動作するようプロジェクトルート検出に __file__ を使用。特殊な配置や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化すること。
- calendar_update_job / ETL 等は jquants_client の外部実装に依存するため、本リポジトリ単体での完全な動作には追加のクライアント実装が必要。

署名
- 初版リリース: kabusys チーム (自動生成ドキュメントに基づく)