# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。パッケージ全体の骨格と主要なデータ収集／特徴量計算機能を実装しました。

### 追加
- パッケージ初期化
  - kabusys パッケージの基本エントリポイントを追加。__version__ = "0.1.0"、公開 API として data/strategy/execution/monitoring を定義。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルート検出ロジック: .git または pyproject.toml を探索してルートを特定（CWD に依存しない）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーを強化:
    - コメント行、export プレフィックス、シングル/ダブルクォート・バックスラッシュエスケープ、インラインコメント処理をサポート。
  - Settings クラスを実装し、J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベルなどのプロパティを提供。
    - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と便利なブールプロパティ（is_live 等）。

- データ取得クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - レート制限 (120 req/min) を守る固定間隔スロットリング（_RateLimiter）。
    - リトライ（指数バックオフ、最大3回）。429 の場合は Retry-After を尊重。
    - 401 時はリフレッシュトークンで自動的に id_token を更新して 1 回リトライ。
    - ページネーション対応で全ページを取得。
    - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装。
    - DuckDB 保存用関数: save_daily_quotes, save_financial_statements, save_market_calendar を実装（ON CONFLICT DO UPDATE により冪等性を担保）。
    - 値変換ユーティリティ (_to_float, _to_int) を実装し、不正な値や空文字列に堅牢。
    - 取得時に fetched_at を UTC タイムスタンプで記録（Look-ahead bias 対策のための取得時刻保存）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS 収集パイプラインを実装。
    - RSS フィード取得（fetch_rss）：gzip サポート、Content-Length / max サイズチェック（10MB）、XML パース（defusedxml 使用）により安全に処理。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームと到達先がプライベートアドレスでないかを検査するカスタムハンドラ（_SSRFBlockRedirectHandler）。
      - ホスト名の DNS 解決を行い、プライベート/ループバック/リンクローカル/マルチキャストを拒否。
    - ペイロード保護:
      - 最大受信バイト数チェック、gzip 展開後のサイズ再検査（Gzip bomb 対策）。
      - defusedxml による XML 攻撃防御。
    - 記事整形:
      - URL 除去・空白正規化の前処理（preprocess_text）。
      - 記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証（utm_* 等のトラッキングパラメータを除去して正規化）。
    - DB 保存:
      - save_raw_news: チャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を実行し、新規挿入された記事IDを正確に返す。トランザクション管理とロールバックを実装。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けをバルク挿入。チャンク分割と重複除去、トランザクション管理を実装。
    - 銘柄抽出:
      - 4桁数字パターン (\b\d{4}\b) を候補として抽出し、既知銘柄セットでフィルタリングする extract_stock_codes を実装。
    - run_news_collection: 複数ソースの総合収集ジョブを実装（ソース単位で独立処理・例外隔離）。

- リサーチ／特徴量 (kabusys.research)
  - feature_exploration モジュールを追加:
    - calc_forward_returns: DuckDB の prices_daily を参照して将来リターン（1/5/21 営業日等）を一括クエリで計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足／定数分散を考慮して None を返す。
    - rank: 同順位は平均ランクを与えるランク関数（丸めで浮動小数点誤差対策）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - factor_research モジュールを追加:
    - calc_momentum: mom_1m/mom_3m/mom_6m および 200日移動平均乖離率 (ma200_dev) を計算。必要なデータ不足時は None を返す。
    - calc_volatility: 20日 ATR（atr_20）, 相対ATR (atr_pct), 20日平均売買代金 (avg_turnover), 出来高比 (volume_ratio) を計算。true_range の NULL 伝播を正確に制御。
    - calc_value: raw_financials から target_date 以前の最新財務データを用いて PER / ROE を計算（EPS が 0 または欠損の場合は None）。
  - research パッケージの __all__ を整備してユーティリティを公開（zscore_normalize を data.stats からインポートして再公開）。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の DDL を実装（Raw Layer の主要テーブル作成文を追加）。
    - raw_prices, raw_financials, raw_news, raw_executions（部分）が含まれる（DataSchema.md に基づく3層構造の基礎）。

### 改良（設計・品質）
- 外部 API 呼び出し（発注など）にはアクセスしない設計を明示（Research / Factor モジュール）。
- ロギングを幅広く追加し、操作追跡・障害解析が容易に。
- 型ヒントとドキュメンテーションストリングを豊富に記載し、可読性とメンテナンス性を向上。
- トランザクションとチャンク処理により DB 操作の堅牢性とパフォーマンスに配慮。
- セキュリティ対策: SSRF、XML 攻撃、レスポンスサイズ攻撃などに対する複数の防御策を実装。

### 修正
- （初回リリースのため特定のバグ修正履歴はなし）

### 破壊的変更
- なし

---

今後の予定（例）
- schema モジュールの Execution 層テーブル定義を完成させる
- strategy / execution / monitoring の実装（発注ロジック、ポジション管理、監視）
- 単体テストと CI 設定の追加
- ドキュメントの整備（使用例・API リファレンス）