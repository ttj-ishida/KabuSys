# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
このファイルではパッケージの主要リリース内容（機能追加・設計方針・重要な環境変数等）を日本語でまとめています。

※ バージョンはパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。モジュール化された日本株自動売買プラットフォームのコア機能群を導入しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - サブパッケージの想定外部公開: data, strategy, execution, monitoring（src/kabusys/__init__.py の __all__）。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に自動でルートを探す実装。cwd に依存しない自動読み込み。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを抑制可能。
  - 必須環境変数取得メソッド（_require）により未設定時は明示的な例外を発生。
  - 検証済み設定:
    - 環境種別: KABUSYS_ENV（development/paper_trading/live）
    - ログレベル: LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - 主要環境変数（例）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）

- Data レイヤー（src/kabusys/data）
  - J-Quants API クライアント (src/kabusys/data/jquants_client.py)
    - API 呼び出しユーティリティ（_request）を実装。JSON パースとエラーハンドリングを備える。
    - レートリミッタ（120 req/min 相当）の実装（固定間隔スロットリング）。
    - 再試行（リトライ）ロジック：指数バックオフ、最大 3 回、HTTP 408/429/5xx を対象。
    - 401 応答時のトークン自動リフレッシュ（get_id_token による）をサポートし、1 回のみリトライ。
    - ページネーション対応で fetch_* 系関数を提供:
      - fetch_daily_quotes (日足)
      - fetch_financial_statements (財務)
      - fetch_market_calendar (マーケットカレンダー)
    - DuckDB への冪等保存関数を提供（ON CONFLICT DO UPDATE を利用）:
      - save_daily_quotes -> raw_prices テーブル
      - save_financial_statements -> raw_financials テーブル
      - save_market_calendar -> market_calendar テーブル
    - 型変換ユーティリティ: _to_float, _to_int（不正値を None に扱う）
    - fetched_at を UTC ISO8601 で記録し、Look-ahead Bias 防止の考慮。

  - ニュース収集モジュール (src/kabusys/data/news_collector.py)
    - RSS フィード取得・パース・前処理・DuckDB 保存までの一連処理を実装。
    - セキュリティ対策:
      - defusedxml を使った XML パース（XML Bomb 対策）。
      - SSRF 対策（URL スキーム検証、プライベートアドレス検出、リダイレクト時の検査）。
      - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後チェック。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去）。
    - 記事 ID は正規化 URL の SHA-256 の先頭 32 文字で生成し冪等性を保証。
    - テキスト前処理（URL 除去、空白正規化）。
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING を使い、実際に挿入された記事 ID リストを返す。チャンク & 単一トランザクション。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存。
    - 銘柄コード抽出（4桁数字）機能と既知銘柄セットによるフィルタ。
    - 統合ジョブ run_news_collection により複数ソースを逐次処理（ソース単位で独立エラーハンドリング）。

  - スキーマ定義 (src/kabusys/data/schema.py)
    - DuckDB 用 DDL を定義（Raw Layer を中心に初期テーブルを追加）。
    - 定義済みテーブル（主なもの）:
      - raw_prices, raw_financials, raw_news, raw_executions（raw_executions はファイル末尾で定義中）
    - テーブル設計は Raw / Processed / Feature / Execution の 3 層（コメント）に基づく。

- Research レイヤー（src/kabusys/research）
  - 特徴量探索モジュール (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: DuckDB の prices_daily テーブルを参照して将来リターン（複数ホライズン）を一度に計算する。
      - horizons の検証（正の整数かつ <=252）。
      - SQL 内で LEAD を利用して効率的に取得。
    - calc_ic: ファクター値と将来リターンからスピアマンランク相関（IC）を計算。無効データ除外、3件未満は None。
    - rank: 同順位は平均ランクを割り当てるランク関数（丸めにより ties 検出を安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算（None/非有限値を除外）。
    - すべて標準ライブラリのみで実装し、DuckDB への読み取りのみを想定（外部 API へはアクセスしない設計）。
  - ファクター計算モジュール (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を計算。
      - 必要データが不足する場合は None を返す。
    - calc_volatility: 20日 ATR（平均 true range）、相対 ATR、20日平均売買代金、出来高比率を計算。
      - true_range の NULL 伝播を正しく扱い cnt ベースで判定。
    - calc_value: raw_financials から直近の財務（report_date <= target_date）を取得し PER / ROE を計算。
      - EPS=0 や欠損時は PER を None とする。
    - 各関数とも prices_daily / raw_financials テーブルのみ参照、結果を (date, code) キーの dict リストで返却。
  - research パッケージのエクスポート（src/kabusys/research/__init__.py）で主要ユーティリティを公開:
    - calc_momentum, calc_volatility, calc_value, zscore_normalize（データ側から）, calc_forward_returns, calc_ic, factor_summary, rank

### 変更 (Changed)
- 初回リリースにつき過去の変更履歴はなし。

### 修正 (Fixed)
- 初回リリースにつき過去の修正履歴はなし。

### セキュリティ (Security)
- ニュース収集での SSRF 対策、受信サイズ制限、defusedxml による XML パース強化を実施。
- 外部 API（J-Quants）呼び出し時の認証トークン管理と安全な再取得を実装。

### マイグレーション / 注意事項
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings により必須とされる（未設定時は ValueError が発生）。
- .env 自動読み込み:
  - プロジェクトルートが検出できない場合は自動ロードをスキップ。
  - OS 環境変数は保護され、.env/.env.local により上書きされない（ただし .env.local は override=True のため .env より優先）。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（テスト用途を想定）。
- DuckDB スキーマ:
  - 初期スキーマは Raw Layer を中心に定義済み。利用前にスキーマ初期化処理（schema モジュールの適用）を推奨。
- J-Quants API のレート制限・リトライ:
  - 内部で 120 req/min 相当の固定間隔スロットリングと指数バックオフが実装されています。大量取得時は処理時間に注意してください。

---

今後のリリースでは、strategy / execution / monitoring の具体的な実装や、Feature Layer / Execution Layer の完全な DDL、より多くのファクター・指標・通知機能の追加を予定しています。必要があれば、この CHANGELOG を更新して差分を明確にします。