CHANGELOG
=========

すべての重要な変更をこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。  
現在のバージョンはパッケージメタデータに記載の通り 0.1.0 です。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-28
--------------------

Added
- 初期リリース: KabuSys 日本株自動売買システムのコア実装を追加。
  - パッケージエントリポイント（kabusys.__init__）。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート判定: .git / pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - 強力な .env パーサ実装（export 形式対応、シングル/ダブルクォート内のエスケープ、インラインコメント処理）。
  - override / protected 機能により OS 環境変数の保護と .env.local による上書きをサポート。
  - Settings クラスを公開。J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの取得とバリデーションを提供。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を用いた記事集約と銘柄別センチメントスコア算出機能を実装。
    - JST ベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）と UTC 変換を実装。
    - OpenAI（gpt-4o-mini）へのバッチ送信（最大 _BATCH_SIZE=20 銘柄）、JSON Mode による厳密な出力期待。
    - リトライ（429、ネットワーク、タイムアウト、5xx）をエクスポネンシャルバックオフで実装。失敗時はスキップしフェイルセーフで継続。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - DuckDB の executemany に関する互換性（空リスト回避）を考慮したテーブル書き換えロジック（DELETE → INSERT）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードフィルタで raw_news のタイトルを抽出し、OpenAI で JSON 出力（{"macro_sentiment": ...}）を期待。
    - API 呼び出しはリトライ/バックオフを実装。API 異常時は macro_sentiment=0.0 でフェイルセーフ継続。
    - 計算結果は冪等に market_regime テーブルへ書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス防止設計（datetime.today()/date.today() を直接参照しない、prices_daily は date < target_date 条件）。
- リサーチモジュール（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR）・流動性指標、バリュー（PER, ROE）を DuckDB 上で計算する関数を実装。
  - feature_exploration: 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、ランク変換（同順位は平均ランク）、ファクター統計サマリーを実装。
  - 設計上、外部 API/発注とは無関係にデータのみ参照する安全な実装。
- データプラットフォーム（kabusys.data）
  - market calendar 管理（calendar_management）
    - market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 未取得時は曜日ベースのフォールバック（週末を非営業日）を一貫して使用。
    - カレンダー夜間更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得・バックフィル・健全性チェックを行い冪等保存。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスで ETL 実行結果（取得数・保存数・品質問題・エラー）を表現。
    - 差分取得ロジック、backfill の概念、品質チェックとの連携設計を導入。
  - etl モジュールから ETLResult を公開再エクスポート（kabusys.data.etl）。
- 多くの関数/処理で DuckDB 互換性や実運用を意識した堅牢化（NULL/データ不足ハンドリング、ログ出力、例外時のロールバックと警告）。

Changed
- N/A（初回リリースのため変更履歴はなし）

Fixed
- N/A（初回リリースのため修正履歴はなし）

Security
- 環境変数取り扱いに関して、API キーが未設定の場合は明確な ValueError を発生させることで誤動作を防止（OpenAI API キー、Slack トークン等）。
- .env の読み込みは OS 環境変数を保護する仕組み（protected set）を導入。

Notes / Implementation details
- 時刻・日付の扱いはすべて date / naive datetime を使用し、タイムゾーン混入を避ける設計（ニュースウィンドウは JST 基準を UTC naive に変換して DB 比較）。
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON Mode を利用した厳密な解析を行う。テストおよび差替えのために _call_openai_api をモジュール内で独立している。
- 多数の設計判断（ルックアヘッドバイアス回避、フェイルセーフ、部分失敗時のデータ保護等）はソースドキュメント内に明記。

今後
- 継続的なテスト追加（DB モック、OpenAI モック）や、UI/監視・発注機能の実装予定。
- PBR や配当利回りなど、バリューファクターの拡張予定。

References
- パッケージバージョン: src/kabusys/__init__.py の __version__ = "0.1.0" に準拠。