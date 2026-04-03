# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-04-03

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージのトップレベル宣言に __version__ = "0.1.0" を設定し、主要サブパッケージを公開（data, research, ai などを __all__ で列挙）。
- 環境設定モジュール (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出ロジックを導入（.git または pyproject.toml を基準）。カレントワーキングディレクトリに依存しない自動ロード。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮して値を復元。
    - クォートなしの場合のインラインコメント処理（'#' の前が空白/タブならコメントとみなす）。
  - 環境変数保護機能: OS の既存キーを protected として .env.local の上書きから保護。
  - Settings クラスを提供し、主要設定プロパティを型付きで公開（例: jquants_refresh_token, kabu_api_password, kabu_api_base_url, line_channel_access_token 等）。
  - 各種設定のバリデーションとデフォルト値:
    - KABUSYS_ENV: development / paper_trading / live のみ許可。
    - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許可。
    - パス設定（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH）を Path 型で取得。
    - モニタリング閾値（CPU/MEM/DISK）を float で取得。
    - kill_flag_clear_on_start フラグ処理（"1" で True）。
- データ関連 (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定 API を実装。
    - market_calendar テーブルが存在しない場合は曜日ベース（土日休）をフォールバックとして利用する一貫した挙動。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) を導入して無限ループを防止。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等に更新（バックフィル・健全性チェック付き）。
  - ETL / パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（取得数・保存数・品質問題・エラーの要約を保持）。
    - 差分取得、backfill、品質チェックのための設計方針を実装。
    - DuckDB の互換性と制約（executemany に空リストを渡せない問題等）を考慮した実装。
  - jquants_client 経由の保存処理に対するエラーハンドリング（例外ログ記録）を実装。
- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - raw_news & news_symbols を集計して銘柄ごとに記事をまとめ、OpenAI (gpt-4o-mini) にバッチ送信して銘柄ごとにセンチメント（-1.0〜1.0）を算出。
    - チャンク単位での送信（最大 _BATCH_SIZE=20 銘柄）と、1銘柄当たりトークン肥大化対策（最大記事数・最大文字数トリム）を実装。
    - JSON mode での応答処理と堅牢なパースロジック（前後に余計なテキストが混入した場合は最外の {} を抜き出して復元）。
    - エラー（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフとリトライ制御。リトライ限界超過時は当該チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスバリデーション: results キー・型・既知コード・数値チェックを行い、スコアを ±1.0 にクリップ。
    - ai_scores テーブルへの書き込みは部分失敗時に既存スコアを保護するため、対象コードのみ DELETE → INSERT を実行（トランザクション）。
    - テスト容易性: _call_openai_api を unittest.mock.patch で差し替え可能。
  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次でレジーム（bull/neutral/bear）判定。
    - マクロ記事はキーワードベースで抽出（複数のマクロキーワードリストを実装）。
    - OpenAI 呼び出しは gpt-4o-mini を使用し、JSON 応答を期待。API失敗時は macro_sentiment=0.0（中立）へフォールバック。
    - ma200_ratio 計算は target_date 未満のデータのみを使いルックアヘッドバイアスを排除。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK ハンドリング。
- リサーチ / ファクター関連 (kabusys.research)
  - factor_research
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離率 (ma200_dev) を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率等のボラティリティ・流動性指標を計算。
    - calc_value: raw_financials から直近財務指標を取得し PER/ROE を計算（EPS が無効な場合は None）。
    - すべて DuckDB SQL ベースで実装し、本番注文や外部 API にはアクセスしない設計を明確化。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得するSQLを実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。利用可能レコードが 3 未満の場合は None を返す。
    - rank: 同順位は平均ランクを割り当てる安定したランク関数（丸め処理で ties 検出の堅牢化）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出する統計サマリーを実装（None値は除外）。
- ロギングと堅牢性
  - 各モジュールで詳細なログメッセージを追加（info/debug/warning/exception を適宜使用）。
  - ルックアヘッドバイアス対策として、各日付計算は datetime.today()/date.today() を参照しない設計（target_date を明示的に引数で渡す方式）。
  - API キー未設定時は ValueError を投げることで呼び出し側に明示的なエラーを通知（OpenAI API キー等）。
- DuckDB 互換性とトランザクション設計
  - executemany の空リスト制約（DuckDB 0.10）を回避するためのチェックを追加。
  - 部分失敗時に既存データを不必要に消さない書き換え戦略（対象コードのみの DELETE → INSERT）を採用。

Fixed
- N/A（初版リリースのため、既知のバグ修正履歴はなし）

Changed
- N/A（新規導入）

Security
- 環境変数取得で必須項目が未設定の場合は明示的に例外を投げるようにし、誤設定による静かな失敗を防止。

Notes / Migration
- 初期リリースのため、API（関数シグネチャや返り値）をそのまま利用可能。将来のマイナーバージョンで破壊的変更を行う場合はメジャーアップデートで通知予定。
- OpenAI を利用する機能を使うには OPENAI_API_KEY を環境変数（または関数引数）で設定してください。
- .env の自動読み込みはパッケージ導入先のプロジェクトルート検出に依存します。自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

----

今後の予定（例）
- モニタリング / 実行（execution, monitoring）周りの詳細実装およびドキュメント整備
- J-Quants クライアントの拡張と ETL のより詳細な品質チェックルール追加
- テストカバレッジの拡充（特に OpenAI 呼び出しと DB トランザクション周り）

もし CHANGELOG に追記してほしい点（リリース日や追加で強調したい設計決定など）があれば教えてください。