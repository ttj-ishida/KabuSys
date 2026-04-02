CHANGELOG
=========

すべての重要な変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に従って記載します。  
日付はコードベース内の現状から推測した初回リリース日を用いています。

Unreleased
----------
- なし（現状のコードは初期リリース相当です）

0.1.0 - 2026-04-02
------------------
概要: 初期リリース。日本株自動売買システム「KabuSys」のコアモジュール群を実装・公開。DuckDB を用いたデータ操作、J-Quants からのデータ取得を想定した ETL、マーケットカレンダー管理、ファクター計算、ニュースに対する LLM ベースのセンチメント評価、および市場レジーム判定などを含む。

Added
- パッケージ初期公開
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"、パブリックなサブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。
- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化（テスト支援）。
  - .env パースの堅牢化（export プレフィックス対応、クォート/エスケープ対応、インラインコメントの扱い、保護された OS 環境変数の上書き制御）。
  - Settings クラスによる設定プロパティを提供（J-Quants トークン、kabu API、Slack、データベースパス、監視閾値、環境/ログレベル検証・ユーティリティプロパティ）。
- AI / ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄別にニューステキストを構築。
  - OpenAI（gpt-4o-mini、JSON mode）を用いた銘柄毎のセンチメントスコア算出。
  - バッチ処理（最大 20 銘柄/チャンク）、トークン肥大化対策（記事数・文字数上限）を実装。
  - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ、レスポンスの厳密な JSON バリデーションとスコアクリップ（±1.0）。
  - ai_scores テーブルへの冪等的な置換（該当コードのみ DELETE→INSERT）。部分失敗時に既存スコアを保護する設計。
  - calc_news_window ユーティリティ（JST ベースの収集ウィンドウ計算）。
- AI / 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
  - DuckDB からの時系列参照はルックアヘッド防止（target_date 未満データのみ使用）。
  - OpenAI 呼び出しに対するリトライ/フェイルセーフ（API 失敗時は macro_sentiment=0.0）と、market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
- リサーチ（kabusys.research）
  - ファクター計算（calc_momentum / calc_value / calc_volatility）：prices_daily / raw_financials を用いたモメンタム・バリュー・ボラティリティ指標の算出（MA200、ATR20、PER、ROE、出来高指標等）。
  - 特徴量探索ユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）：将来リターン計算、スピアマン IC、統計サマリー、ランク化ユーティリティを実装。外部依存（pandas 等）無しで標準ライブラリと DuckDB を用いる設計。
- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを参照した is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の判定ロジック。
    - DB データが部分的にしかない場合でも曜日ベースのフォールバックを一貫して使用する実装。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック・ログ出力）。
  - ETL パイプライン（pipeline）
    - ETLResult データクラス（target_date、fetched/saved カウント、品質問題、エラー一覧、to_dict 等）。
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client および quality モジュールと連携）。
  - etl モジュールで ETLResult を再エクスポート。
- DuckDB ベースの堅牢な SQL/ウィンドウ処理
  - 各モジュールで DuckDB のウィンドウ関数や LEAD/LAG/ROW_NUMBER を利用して効率的に時系列指標を算出。
  - 空集合/データ不足時のフォールバック（None や中立値）を明確化。
- ロギング・例外処理
  - 各処理で詳細な logger 情報を出力。API/DB 書込失敗時の ROLLBACK と警告ログを整備。
  - LLM API の失敗は例外を必ずしも上げずフェイルセーフ（代替値で継続）とする方針。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーを引数で注入可能にすることで、環境変数漏洩リスクの軽減やテスト容易性を向上（明示的な修正というより設計上の配慮）。

注記・設計上の留意点
- ルックアヘッドバイアス防止: LLM・時系列計算ともに内部で datetime.today() / date.today() を直接参照しない（target_date 指定方式）。
- LLM 呼び出しは JSON mode を期待するが、実運用では LLM 応答の不確実性を考慮して冗長なパースロジックと厳格な検証を行っている。
- DuckDB のバージョン差異（executemany での空リスト等）に対する互換性対策が組み込まれている。
- 一部モジュール（strategy, execution, monitoring）はパッケージ公開に含まれているが、今回提示コードには内部実装が含まれていない（将来的な追加を想定）。

今後の予定（推測）
- 実行/発注ロジック（execution）やストラテジ実装（strategy）の追加公開。
- モニタリング・アラート（monitoring）の実装強化（Slack 通知等）。
- jquants_client / quality モジュールとの結合テスト、および OpenAI モデルの運用チューニング。

--- 
（この CHANGELOG は提示されたコード内容からの推測に基づき作成しています。実際のリリースノート作成時はコミット履歴・変更差分を参照して適宜更新してください。）