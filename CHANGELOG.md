# CHANGELOG

すべての変更点は「Keep a Changelog」の方針に従って記載しています。  
重要な変更のみを記載しています。

※本CHANGELOGはコードベースから推測して作成したものであり、実装意図・ドキュメント注釈を基に要約しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20
初回リリース。以下の主要コンポーネントと機能を実装。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを設定（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開 API を __all__ で定義（data, strategy, execution, monitoring の想定モジュールをエクスポート）。

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読込する機能を実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動読み込み。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用フラグ）。
  - .env パーサ実装（export プレフィックス、クォート内エスケープ、インラインコメント処理などをサポート）。
  - .env 読み込み時の上書き制御（override フラグ）と OS 環境変数保護（protected set）を実装。
  - Settings クラスを提供し、主要設定のプロパティを公開（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル 等）。
    - 必須キー未設定時に ValueError を送出する _require を実装。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装（許容値を明示）。

- データ取得・保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
    - レート制限を守る固定間隔スロットリング _RateLimiter（120 req/min）。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 時の自動トークンリフレッシュ（1 回のみ）をサポート。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB に対する冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供。ON CONFLICT による更新を行う。
    - データ整形ユーティリティ (_to_float, _to_int)、UTC の fetched_at 記録等、Look-ahead バイアス対策とトレーサビリティを重視した設計。
  - モジュールレベルの ID トークンキャッシュを実装し、ページネーションや複数リクエストでのトークン再利用を最適化。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news に保存するロジックを実装（デフォルトソース: Yahoo Finance ビジネス RSS）。
  - URL 正規化機能（トラッキングパラメータ削除、クエリソート、フラグメント削除、小文字化）と記事 ID の SHA-256 ハッシュ化（先頭 32 文字）による冪等性確保。
  - defusedxml を用いた XML パース、受信サイズ上限（MAX_RESPONSE_BYTES）や SSRF 回避のためのスキームチェック等のセキュリティ対策。
  - DB へのバルク挿入（チャンク化）とトランザクション統合により効率的・安全に保存。

- リサーチ (src/kabusys/research/*.py)
  - ファクター計算（src/kabusys/research/factor_research.py）を実装。
    - モメンタム（1M/3M/6M リターン、200 日移動平均乖離率）。
    - ボラティリティ／流動性（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）。
    - バリュー（PER、ROE）の取得（raw_financials と prices_daily の組合せ）。
    - 日付範囲バッファや NULL の扱いなど、実運用を考慮した SQL 実装。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）を実装。
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト: 1,5,21 日）対応、SQL ベースで一括取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関（ties の平均ランク処理を含む）。
    - ファクター統計サマリー（factor_summary）および rank ユーティリティを提供。
  - zscore_normalize の再公開を research パッケージで行い、他モジュールから利用可能に。

- 戦略 (src/kabusys/strategy/*.py)
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュールで計算した生ファクター（momentum / volatility / value）を統合し、ユニバースフィルタ（最低株価・最低売買代金）を適用。
    - 正規化:zscore_normalize を利用、±3 でクリップし features テーブルへ日付単位の置換（トランザクション+バルク挿入で原子性）。
    - 参照テーブル: prices_daily, raw_financials。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合し最終スコア final_score を算出。デフォルト重みを実装（momentum:0.40 等）。
    - 重みの受け入れと検証（未知キー・非数値・負値は無視、合計が 1 に再スケール）。
    - スコア変換ユーティリティ（シグモイド変換、組合せの補完ルール: None は中立 0.5）。
    - Bear レジーム判定（AI の regime_score 平均が負かつ十分なサンプルがある場合に BUY を抑制）。
    - BUY シグナル: threshold（デフォルト 0.60）以上を採用（Bear では抑制）。
    - SELL シグナル（保有ポジションのエグジット判定）:
      - ストップロス: 終値 / avg_price - 1 < -8%（最優先）
      - スコア低下: final_score が threshold 未満
      - なお、一部のルール（トレーリングストップ、時間決済）は positions テーブルの拡張が必要で未実装として注記。
    - signals テーブルへ日付単位で置換挿入（トランザクションで原子性を確保）。保有銘柄の SELL を優先して BUY から除外するポリシーを実装。

- データ統計ユーティリティ (src/kabusys/data/stats.py は再公開想定)
  - zscore_normalize が research と strategy より利用される設計。

- DB 操作の堅牢化
  - 各処理でトランザクション（BEGIN/COMMIT/ROLLBACK）を用いて日付単位の置換（DELETE + INSERT/EXECUTEMANY）を行い、冪等性・原子性を保証。
  - 例外発生時のロールバック試行中のログ警告を実装（logger.warning）。

### 変更 (Changed)
- 設計方針の反映
  - ルックアヘッドバイアスを防ぐため、各計算は target_date 時点までのデータのみを用いる方針で実装。
  - 発注（execution）層や外部実行環境への直接依存を持たない層分離（strategy 層は signals テーブル生成までを担当）。

### 修正 (Fixed)
- N/A（初回リリース）

### セキュリティ (Security)
- ニュース収集で defusedxml を使用して XML 攻撃を軽減。
- RSS の受信サイズ上限、URL スキームチェック、トラッキングパラメータ除去等、外部入力に対する安全対策を実装。

### 既知の制限 / TODO
- positions テーブルに peak_price / entry_date 等が未整備なため、トレーリングストップや時間決済の一部条件は未実装（signal_generator に注記あり）。
- execution パッケージは空の __init__.py のみ（発注 API 連携は別タスク）。
- 一部モジュールは research 環境向けで外部ライブラリを使わない設計（pandas などは未使用）。大規模データ処理の最適化は今後の改善余地あり。

---

参考: 実装ファイル一覧（主要）
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/research/factor_research.py
- src/kabusys/research/feature_exploration.py
- src/kabusys/strategy/feature_engineering.py
- src/kabusys/strategy/signal_generator.py
- src/kabusys/strategy/__init__.py

（このCHANGELOGはコード内容の静的解析に基づくため、実際のリリースノートと差分がある可能性があります。）