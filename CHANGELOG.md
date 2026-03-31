CHANGELOG
=========
すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。

フォーマット
-----------
各リリースは日付付きで記載し、Added / Changed / Fixed / Security などの見出しで分類しています。

[Unreleased]
------------
（なし）

[0.1.0] - 2026-03-31
-------------------
初回公開リリース。データ収集・ETL、マーケットカレンダー管理、研究用ファクター計算、AIによるニュースセンチメント解析および市場レジーム判定などの主要機能をまとめて提供します。

Added
- パッケージ基盤
  - kabusys パッケージの公開（__version__ = 0.1.0）。
  - パッケージエクスポート: data, strategy, execution, monitoring を __all__ として準備。

- 環境設定/設定管理（kabusys.config）
  - .env ファイルおよび環境変数自動ロード機能を実装（プロジェクトルートの検出に .git / pyproject.toml を使用）。
  - 高度な .env パーサー実装：export 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 実行環境等の設定値取得用プロパティを定義。必須環境変数未設定時に明示的なエラーを出す _require を実装。
  - KABUSYS_ENV の検証（development / paper_trading / live）と LOG_LEVEL の検証ロジックを追加。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（calendar_management）:
    - JPX 市場カレンダー管理 API 統合のためのユーティリティ群を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装し、market_calendar テーブルのデータを優先、未登録日は曜日ベースでフォールバックする一貫したロジックを提供。
    - calendar_update_job を実装し、J-Quants から差分取得→冪等保存（ON CONFLICT 相当）する夜間バッチ処理を実装。バックフィル・健全性チェックを実装。
  - ETL パイプライン（pipeline）:
    - ETLResult データクラスを実装し、ETL の取得件数・保存件数・品質チェック結果・エラー一覧を格納・出力可能に。
    - ETL 実装方針に沿った差分更新・バックフィル・品質チェックのための土台を追加。
  - etl モジュール用の公開インターフェース（etl）で ETLResult を再エクスポート。

- AI（kabusys.ai）
  - ニュース NLP（news_nlp）:
    - raw_news / news_symbols を集約して銘柄ごとのニュースを結合し、OpenAI（gpt-4o-mini）によるバッチセンチメント評価を行う score_news を実装。
    - API 呼び出しの再試行（429, ネットワーク断, タイムアウト, 5xx）・指数バックオフ・レスポンスバリデーション（JSON 抽出、results 構造、コード確認、数値検証）を実装。
    - スコアは ±1.0 にクリップ、部分成功時に既存スコアを保護するため DELETE→INSERT の部分置換を採用。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能に（_call_openai_api のモックポイント）。
    - ニュース収集ウィンドウ（JST）計算ユーティリティ calc_news_window を実装（前日 15:00 JST ～ 当日 08:30 JST）。
  - 市場レジーム判定（regime_detector）:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成し日次の市場レジーム（bull/neutral/bear）を算出する score_regime を実装。
    - MA 計算、マクロ記事抽出、OpenAI への問い合わせ（リトライ／フェイルセーフ）および market_regime テーブルへの冪等書き込みを実装。
    - API エラー時はマクロセンチメントを 0.0 にフォールバックする設計。
    - news_nlp と処理を分離し、モジュール結合を避ける設計（OpenAI 呼び出し実装は別個）。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M モメンタム、および 200 日 MA 乖離率を計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の EPS／ROE を取得し PER/ROE を計算（EPS 欠損時は None）。
    - すべて DuckDB SQL を用いて実装し、外部 API 呼び出しはなし。結果は (date, code) ベースの dict リストを返す。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21）での将来リターンを計算。
    - calc_ic: スピアマンランク相関による IC を計算（ties は平均ランクで処理）。
    - rank / factor_summary: ランク付けユーティリティと基本統計量（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

Changed
- ロギングと失敗耐性の強化
  - 多くのモジュールで詳細なログ出力を追加し、外部 API エラー時にも処理が継続するフェイルセーフ設計を採用。
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等性を意識した実装。

Fixed
- （リリース時点で既知のバグ修正は無し。内部的な例外ハンドリングやログ出力の強化を反映。）

Security
- 明示的なセキュリティ修正は無し。注意点として OpenAI / J-Quants / kabuAPI などの秘密情報は環境変数で管理することを推奨。Settings._require により必須トークンが未設定だと明示的エラーとなる。

互換性 / マイグレーションノート
- 環境変数（必須）
  - OpenAI: OPENAI_API_KEY（score_news / score_regime で必須）
  - J-Quants: JQUANTS_REFRESH_TOKEN
  - kabuステーション: KABU_API_PASSWORD（および必要なら KABU_API_BASE_URL）
  - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - データベースパス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（監視用）
- .env 自動読み込みはデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を利用した SQL 実行結果の型（特に日付）はモジュール側で変換処理を行っていますが、DB スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials 等）が必要です。
- score_news / score_regime は OpenAI API を呼び出すためネットワークアクセスが必要。単体テストでは _call_openai_api をパッチして差し替え可能です。

過去の開発（推測）
-----------------
本リリースに至るまでに以下のような段階的開発が行われたと推測されます（参考情報、厳密な履歴ではありません）。

[0.0.3] - 2026-03-20
- research モジュールの追加（factor_research, feature_exploration）。
- z-score 正規化ユーティリティの統合インポートを追加。

[0.0.2] - 2026-03-15
- AI モジュールの追加（news_nlp, regime_detector）。
- OpenAI 統合・JSON mode を用いたレスポンス処理の実装。

[0.0.1] - 2026-03-10
- 初期スケルトン（config, data pipeline 基礎, パッケージ構成）。
- ETLResult と pipeline の骨格実装。

免責事項
--------
この CHANGELOG は提供されたソースコードの内容から推測して作成したもので、実際のコミット履歴やリリースノートとは差異がある可能性があります。必要であれば実際の Git 履歴に基づく正確な CHANGELOG を生成しますので、その場合はリポジトリのコミットログを提供してください。