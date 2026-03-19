# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはプロジェクトのリリース履歴を簡潔に把握するためのものです。

## [0.1.0] - 2026-03-19

初回リリース。

### Added
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__init__ に __version__ = "0.1.0"、公開 API 指定）。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を探索してルートを特定）。
  - .env の行パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメントの扱いを考慮）。
  - 読み込み順序の定義: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化にも対応。
  - Settings クラスを提供し、J-Quants トークン、kabuステーション API パスワード、Slack トークン・チャンネル、DB パス等をプロパティとして安全に取得。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）や is_live / is_paper / is_dev のユーティリティを実装。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レートリミット制御（120 req/min 固定間隔スロットリング）を導入。
  - 再試行ロジック（指数バックオフ、最大 3 回）、および 408/429/5xx に対するリトライ戦略を実装。
  - 401 受信時にリフレッシュトークンから自動で ID トークンを再取得して 1 回リトライする仕組みを追加。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）を実装。
  - 取得データを DuckDB に冪等に保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT DO UPDATE を使用）。
  - データ変換ユーティリティ (_to_float, _to_int) を実装し、不正値・空値を安全に扱う。
  - データ取得時の fetched_at を UTC で記録し、Look-ahead Bias の検証を容易に。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを収集して raw_news テーブルへ保存するモジュールを実装。
  - セキュリティ対策: defusedxml による XML パース、SSRF 対策（リダイレクト先のスキーム/ホスト検査）、ホストがプライベート IP の場合は拒否。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）や gzip 圧縮対応、Gzip bomb 対策を実装。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と、それに基づく SHA-256(先頭32文字) の記事 ID 生成を導入し冪等性を担保。
  - テキスト前処理（URL 除去・空白正規化）ユーティリティを追加。
  - 銘柄コード抽出ロジック（本文から4桁数字を抽出して known_codes でフィルタ）を実装。
  - DB 保存はチャンク化してトランザクションで処理し、INSERT ... RETURNING を使って実際に挿入された ID / 行数を正確に取得する実装。
  - RSS 収集ジョブ run_news_collection を提供し、各ソースごとに個別ハンドリング（1 ソース失敗しても他は継続）。
- リサーチ / ファクター計算（kabusys.research）
  - 特徴量探索モジュール（feature_exploration）を追加。
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、SQL LEAD を利用して高速取得）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンランク相関、欠損/finite 判定、最小サンプルチェック）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸め処理で ties 回避）。
    - ファクター統計 summary を計算する factor_summary（count/mean/std/min/max/median）。
  - ファクター計算モジュール（factor_research）を追加。
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）を SQL ウィンドウ関数で算出。データ不足時は None。
    - calc_volatility: 20日 ATR（true range の平均）、atr_pct（ATR/close）、20日平均売買代金、出来高比率を計算。NULL 伝播やカウント条件を考慮。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0 または欠損の場合は None）。
    - すべて DuckDB の prices_daily / raw_financials を参照する設計で、本番発注 API へアクセスしないように設計。
  - 研究用公開 API をまとめたパッケージ初期化（kabusys.research.__init__）を提供。
- DuckDB スキーマ（kabusys.data.schema）
  - Raw レイヤー（raw_prices, raw_financials, raw_news, raw_executions など）向けの DDL を定義するモジュールを追加（テーブル定義と初期化用のスクリプトを保持）。
  - 各カラムに対する型・チェック制約（NULL/PRIMARY KEY/チェック制約）を含む定義。

### Security
- ニュース収集において SSRF 対策を複数レイヤで実装:
  - リクエスト前のホスト検査、リダイレクトハンドラでリダイレクト先検査、プライベート/ループバック/リンクローカルの排除。
  - defusedxml を用いて XML 関連攻撃（XML Bomb 等）を防止。
  - レスポンス読み取り上限と gzip 解凍後のサイズ検査でメモリ DoS を軽減。

### Notes / Design decisions
- 外部依存を極力抑える設計（research モジュールでは pandas 等に依存せず標準ライブラリと DuckDB の SQL を中心に実装）。
- DuckDB へは可能な限り冪等に保存する（ON CONFLICT / DO UPDATE または DO NOTHING を利用）。
- J-Quants API のレート制限や認証フローを考慮した堅牢なクライアント実装を優先。
- ロギングを広く配置し、失敗時の診断や警告が残るよう配慮。

### Breaking Changes
- 初回リリースのため過去互換性に関する変更点はありません。

補足: 各モジュールの docstring に設計方針・制約・期待されるテーブル名等が記載されています。実運用前に .env（.env.example）で必要な環境変数を設定し、DuckDB スキーマ初期化を実行してください。