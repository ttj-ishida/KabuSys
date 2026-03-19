# Changelog

すべての重要な変更をここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。  

- リリースポリシー: 変更はセマンティックバージョニング（MAJOR.MINOR.PATCH）に従います。

## [0.1.0] - 2026-03-19

初回リリース。日本株の自動売買システムに必要なコア機能群を実装しました。主な追加内容は以下の通りです。

### 追加 (Added)
- パッケージ基礎
  - パッケージ初期化とバージョン定義を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - サブパッケージ公開 API を定義（data, strategy, execution, monitoring）。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - プロジェクトルート探索は .git または pyproject.toml を基準に行い、CWD に依存しない。
  - .env のパースを堅牢化（export プレフィックス・シングル/ダブルクォート・バックスラッシュエスケープ・インラインコメントの扱い等に対応）。
  - 環境変数保護（既存 OS 環境変数を保護するオプション）と override 挙動の制御。
  - Settings クラスを提供し、アプリ固有の必須設定をプロパティで取得可能に（J-Quants トークン、kabu API パスワード/URL、Slack トークン/チャネル、DB パス、環境/ログレベル等）。
  - KABUSYS_ENV と LOG_LEVEL のバリデーションを実装。

- データ取得・保存（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装:
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回。HTTP 408/429/5xx をリトライ対象）。
    - 401 の場合は自動でリフレッシュトークンを使って ID トークンを再取得し 1 回リトライ。
    - ページネーション対応（pagination_key を使用）。
    - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスの追跡を可能に。
  - DuckDB への保存ユーティリティを実装（冪等性を確保するため ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes (raw_prices)
    - save_financial_statements (raw_financials)
    - save_market_calendar (market_calendar)
  - データ型変換ヘルパーを実装（_to_float, _to_int）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存する機能を実装。
  - 安全対策・前処理:
    - defusedxml による XML の安全パース（XML Bomb 等の防御）。
    - URL 正規化（utm_* 等のトラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント除去、クエリパラメータソート）。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を担保。
    - HTTP/HTTPS 以外のスキームを拒否し SSRF のリスクを低減。
    - 最大受信バイト制限（10 MB）でメモリ DoS を防御。
    - DB へのバルク挿入はチャンク化（_INSERT_CHUNK_SIZE）して効率化。
  - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを追加。

- リサーチ（研究）機能 (src/kabusys/research/)
  - factor_research.py:
    - モメンタム（1M/3M/6M リターン、200日移動平均乖離率）
    - ボラティリティ（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - バリュー（PER、ROE。raw_financials と prices_daily を組合せ）
    - DuckDB を用いた SQL ベースの計算実装（prices_daily / raw_financials のみ参照）
  - feature_exploration.py:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman の ρ）計算（ランク相関、ties は平均ランクで処理）
    - ファクター統計サマリー（count/mean/std/min/max/median）
    - ランク変換ユーティリティ
  - research パッケージの __all__ を整備し、外部から使いやすく公開。

- 戦略関連 (src/kabusys/strategy/)
  - feature_engineering.py:
    - research 側で計算した生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（冪等）。トランザクションで原子性を確保。
  - signal_generator.py:
    - features と ai_scores を統合して最終スコア（final_score）を計算し、BUY/SELL シグナルを生成。
    - デフォルト重み・閾値、重みの検証と再スケール処理を実装。
    - Bear レジーム検出（ai_scores の regime_score 平均が負の場合。サンプル数閾値あり）。
    - BUY シグナル閾値（デフォルト 0.60）。Bear 時は BUY 抑制。
    - SELL 判定（ストップロス -8% 優先、スコア低下によるエグジット）。
    - positions / prices_daily / ai_scores を参照して SELL を決定。signals テーブルへ日付単位で置換（冪等）。
  - strategy パッケージの __all__ を整備。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- RSS パーサに defusedxml を使用し、XML 関連攻撃を軽減。
- ニュース URL の正規化およびスキーム制限により SSRF・追跡パラメータからの情報漏洩リスクを低減。
- J-Quants クライアントでタイムアウト・リトライ・レート制御を実装し、外部 API 安定性を向上。

### 既知の制約・注意点 (Notes)
- DB スキーマに依存: 本リリースは以下のテーブル構造（存在）を前提とします（詳細はコード内 SQL 参照）。
  - prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news 等。
- zscore_normalize は kabusys.data.stats に実装されている前提で利用しています（今回提示コードには未掲載）。
- signal_generator の一部エグジット条件（トレーリングストップや時間決済）は positions テーブルに peak_price / entry_date 等の追加情報がないため未実装。
- J-Quants クライアントは外部ネットワークに依存します。テスト時は settings.jquants_refresh_token のモックや KABUSYS_DISABLE_AUTO_ENV_LOAD 等を活用してください。
- 自動 .env ロードはプロジェクトルートの検出に依存するため、配布環境では環境変数を明示的に設定することを推奨します。

### 今後の予定 (Next)
- 追加・改善候補:
  - execution 層（kabu ステーション連携）の実装・テスト。
  - monitoring モジュール（Slack 通知・稼働監視）の実装。
  - feature_engineering / signal_generator のバックテスト・パラメータ探索機能追加。
  - positions テーブルの拡張（peak_price, entry_date）に伴うトレーリングストップ等の実装。
  - 単体テスト・CI の整備、外部 API 呼び出しの統合テスト。

---

（本 CHANGELOG はコードベースからの実装内容を推測して作成しています。実際のリリースノートとして利用する際は、差分やコミットログを参照して必要に応じて補正してください。）