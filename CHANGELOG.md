# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠します。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システムのコアライブラリを追加しました。主な追加内容は以下の通りです。

### Added
- パッケージのメタ情報
  - kabusys.__version__ を "0.1.0" として定義。
  - パッケージの公開 API（__all__）を定義。

- 環境変数・設定管理モジュール（kabusys.config）
  - .env ファイルと環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（__file__ 起点で探索）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化をサポート。
    - .env の行パースで export プレフィックス、クォート内のエスケープ、インラインコメント等に対応。
    - 既存 OS 環境変数を保護する protected 機構を実装。
  - Settings クラスを提供（J-Quants / kabu / Slack / DB パス / システム設定等のプロパティ）。
    - 必須設定未存在時は ValueError を発生させる _require() を採用。
    - KABUSYS_ENV（development/paper_trading/live）および LOG_LEVEL の検証ロジックを実装。
    - duckdb/sqlite のデフォルトパスを設定するプロパティを提供。

- Data モジュール — J-Quants クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ（_request）を実装。
    - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
    - 再試行（指数バックオフ、最大 3 回）を実装。408/429/5xx をリトライ対象に設定。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライする仕組み（無限再帰回避）。
    - ページネーション対応の fetch_*（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。
    - fetched_at を UTC ISO8601 形式で記録。
    - PK 欠損行のスキップ、冪等性のための ON CONFLICT ... DO UPDATE を使用。
  - 入出力ユーティリティ (_to_float, _to_int) を実装し、不正な値を安全に None に変換。

- Data モジュール — ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・パース・正規化・保存フローを実装。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、プライベートホスト検査、リダイレクト検査ハンドラ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）や gzip 解凍後のサイズ検査を導入。
    - テキスト前処理（URL 除去、空白正規化）。
    - DuckDB へチャンク挿入し INSERT ... RETURNING を利用して実際に挿入された記事 ID を返す（save_raw_news）。
    - news_symbols（記事と銘柄の紐付け）をバルク挿入で保存する関数を実装（重複除去、チャンク化）。
    - 銘柄コード抽出ユーティリティ（4桁数字の抽出と known_codes によるフィルタ）を提供。
    - run_news_collection により複数ソースを順次処理・保存し、各ソースごとの新規保存数を返す。

- Data モジュール — スキーマ定義（kabusys.data.schema）
  - DuckDB 用テーブル DDL を追加（Raw Layer を中心に定義）。
    - raw_prices, raw_financials, raw_news, raw_executions（raw_executions は定義途中まで含まれるが基本構造を用意）。
  - スキーマ定義は DataSchema.md に基づく3層構造（Raw / Processed / Feature / Execution）の方針を記載。

- Research モジュール（kabusys.research）
  - ファクター計算・特徴量探索を実装。
    - feature_exploration:
      - calc_forward_returns: 1日/5日/21日等の将来リターンを一括 SQL で取得。欠損時は None を返す。
      - calc_ic: Spearman（ランク相関）による Information Coefficient を計算。ties に対して平均ランクで対応。
      - factor_summary: count/mean/std/min/max/median を計算（None 値除外）。
      - rank: 同順位は平均ランクを与えるランク関数（丸め誤差対策で round(v,12) を使用）。
    - factor_research:
      - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev を計算（ウィンドウ不足時は None）。
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true_range の NULL 伝播を明示制御）。
      - calc_value: raw_financials から最新財務データを取得し PER/ROE を計算（EPS が 0/欠損なら PER は None）。
  - いずれも DuckDB 接続を受け取り、prices_daily や raw_financials のみを参照（外部 API にはアクセスしない設計）。

### Security
- news_collector にて SSRF 防止（スキーム検証、プライベートアドレス検査、リダイレクト時の再検査）を実装。
- defusedxml を使用して XML パースの安全性を強化。
- .env ロード時に OS 環境変数を保護する仕組みを実装（既存値を勝手に上書きしない）。
- HTTP クライアントでタイムアウトを設定し、読み込みサイズを制限して DoS 対策を実施。

### Performance
- J-Quants クライアントにレートリミッタを導入して API レート制限を尊重。
- RSS とニュース保存はチャンク化して一括 INSERT（_INSERT_CHUNK_SIZE）を行い DB オーバーヘッドを低減。
- DuckDB 側の集計はウィンドウ関数を活用し一度のクエリで必要な値を取得する設計。

### Reliability / Robustness
- API 呼び出しに対する再試行（指数バックオフ）と 401 での自動トークンリフレッシュを実装。
- JSON デコードエラーや XML パースエラー時は詳細ログを残して安全に失敗（空リスト等）するように設計。
- 入力データの不正・欠損に対する堅牢な処理（PK 欠損行のスキップ、変換関数での None ハンドリング）。
- calc_ic や factor_summary ではレコード不足や分散 0 の場合に None を返す等、数値計算失敗に安全に対処。

### Internal / Documentation
- 各モジュールに詳細な docstring と設計方針を追加（Research / DataPlatform / Strategy に関する注記含む）。
- ロギング（logger）を各関数に埋め込み、処理のトレースを容易に。

### Known Limitations / Notes
- schema.py の raw_executions 定義がファイル末尾で途中まで含まれている（将来的な Execution レイヤー追加を想定）。
- 外部依存を最小化する方針があり、Research の一部は標準ライブラリのみで実装されている（pandas 等を使用していない）。
- 一部の API 操作（例: DuckDB の INSERT ... RETURNING の挙動）は環境に依存するため、実行環境でのテストを推奨。

---

今後のリリースでは以下を予定しています（例）:
- Execution レイヤー（注文・約定・ポジション管理）とそれに伴うスキーマの完成
- Strategy / Backtest 用ユーティリティの追加
- テストカバレッジ拡充と CI 設定
- ドキュメントの追加（使用例、運用手順、環境構築ガイドなど）

もし CHANGELOG に追加・修正したい点があれば教えてください。