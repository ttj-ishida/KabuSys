Keep a Changelog 準拠の CHANGELOG.md（日本語）を作成しました。コードベースの内容から実装機能・設計方針を推測して記載しています。

注意:
- バージョンはパッケージ定義 (src/kabusys/__init__.py) の __version__ = "0.1.0" を基にしています。
- 日付は現在日（2026-04-03）をリリース日として記載しています。
- 実装の設計方針・安全対策（ルックアヘッド対策、冪等書き込み、リトライ/バックオフ等）はコードコメントに基づき要約しています。

CHANGELOG.md
=============

全般ルール
----------
このファイルは Keep a Changelog のフォーマットに準拠しています。  
セマンティックバージョニングに従います。

Unreleased
----------
- 今後の変更・修正はここに記載します。

[0.1.0] - 2026-04-03
-------------------

Added
- 初回公開リリース。
- パッケージ公開 API:
  - kabusys.config: 環境変数/設定管理（.env 自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ、Settings クラス）
    - 自動ロードはパッケクトルート（.git または pyproject.toml）を基準に行う。読み込み順は OS 環境変数 > .env.local > .env。
    - .env パーサは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントに対応。
    - 必須項目の取得で未設定の場合は明示的な ValueError をスロー（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値）や便利プロパティ（is_live / is_paper / is_dev）を提供。
    - データベースパス既定値: DUCKDB_PATH= data/kabusys.duckdb, SQLITE_PATH= data/monitoring.db
    - 監視用ファイルパス / 閾値の設定を提供（PIDファイル、kill フラグ、CPU/MEM/DISK閾値等）。
- kabusys.ai:
  - news_nlp モジュール:
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成し、OpenAI（gpt-4o-mini / JSON Mode）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - タイムウィンドウ計算（JSTベース -> UTC変換）: 前日15:00 JST ～ 当日08:30 JST 相当の収集ウィンドウ。
    - チャンク処理（最大 20 銘柄／API コール）、1銘柄あたり最大記事数と文字数でトリム（安全対策）。
    - API リトライ（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフ実装。
    - レスポンスバリデーション（JSON パース、results フィールド、コード一致、数値チェック）とスコアの ±1.0 クリップ。
    - テスト容易性のため OpenAI 呼び出し箇所を差し替え可能（_call_openai_api のモック化想定）。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成し、market_regime テーブルへ日次で書き込み（ラベル: bull/neutral/bear）。
    - マクロニュースはキーワードリストでフィルタして最新記事を最大件数取得、LLM（gpt-4o-mini）で JSON 出力化された macro_sentiment を取得。
    - API エラー時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
    - 計算・DB 書き込みはルックアヘッドバイアス対策（target_date 未満のデータのみ使用）および冪等（BEGIN/DELETE/INSERT/COMMIT と ROLLBACK 保護）。
- kabusys.research:
  - factor_research:
    - モメンタム（1M/3M/6M リターン、ma200 乖離）、ボラティリティ（20日 ATR、相対ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）を prices_daily / raw_financials から計算するユーティリティを実装。
    - DuckDB SQL を活用し、営業日ベースの窓・LAG/AVG 等を使って効率的に算出。
    - データ不足時は None を返す等の堅牢な挙動。
  - feature_exploration:
    - 将来リターン計算（デフォルトホライズン [1,5,21]）、IC（Spearman の ρ）計算、ランク変換、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリ＋DuckDBで計算。
- kabusys.data:
  - calendar_management:
    - JPX カレンダーの夜間バッチ更新ジョブ（J-Quants API から差分取得 → market_calendar へ冪等保存）。
    - 営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を提供。
    - DB 登録データ優先、未登録日は曜日ベースのフォールバック。探索範囲の上限を設定し無限ループを防止。
    - バックフィルや健全性チェック（将来日付異常時のスキップ）を実装。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラー集約）。
    - 差分更新のためのパイプライン骨格（J-Quants からの差分取得、save_* の冪等保存、品質チェックの収集）を実装。
    - デフォルトのバックフィル設定やカレンダー先読み期間を定義。
  - etl モジュールは pipeline.ETLResult を再エクスポート（外部公開インターフェースの簡略化）。
- テスト／運用面:
  - OpenAI 呼び出し箇所（news_nlp, regime_detector）をモックしやすい設計（内部 _call_openai_api を差し替え可能）。
  - DuckDB の executemany 空リスト制約等を考慮した実装（空の場合は処理をスキップ）。
  - ログ出力（info/debug/warning/exception）を適切に配置。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- OpenAI API キーは引数で注入可能（api_key）で、環境変数 OPENAI_API_KEY もサポート。未設定時は明示的にエラーを返すことで誤動作を防止。

Notes / 設計上の重要点
- ルックアヘッドバイアス対策:
  - AI スコア / レジーム計算 / ファクター計算は target_date を受け取り、内部で date.today() を参照しない設計。
  - DB クエリは target_date 未満や排他的なウィンドウを用い、将来データを参照しないよう厳格に実装。
- 冪等性:
  - market_regime / ai_scores 等への書き込みは削除→挿入（BEGIN/DELETE/INSERT/COMMIT）で冪等に保持・部分失敗時の既存データ保護を考慮。
- フォールバックと堅牢性:
  - API 呼び出し失敗時はフェイルセーフ（スコア 0.0、空結果スキップ等）で継続可能な実装。
  - DuckDB の実行制約に配慮（executemany の空リスト回避など）。
- ロギングとエラーハンドリング:
  - 失敗時には詳細なログを出力し、ROLLBACK の失敗も警告ログ化して監視性を確保。

参考
- パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 主な外部依存: duckdb, openai SDK（gpt-4o-mini モデルを想定）
- 環境変数の主なキー:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能利用時に必須）
  - KABUSYS_ENV（development / paper_trading / live）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

セマンティックバージョニングについて
-------------------------------
- このリリースは初期公開（0.1.0）です。後続の機能追加は Minor、API 互換性の破壊は Major で扱います。

以上。必要であれば、項目の細分化（各モジュール毎の詳細変更点や既知の制限事項）や英語版CHANGELOGも作成します。どの形式で追記しますか？