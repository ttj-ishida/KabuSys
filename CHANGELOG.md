# Changelog

すべての重要な変更をここに記録します。フォーマットは Keep a Changelog に準拠しています。

なお、この CHANGELOG はコードベースの内容から推測して作成しています。

## [Unreleased]

(なし)

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」のコアモジュール群を追加しました。以下は主要な機能・設計上の要点と既知の制限のまとめです。

### 追加 (Added)

- パッケージ初期化
  - src/kabusys/__init__.py
    - バージョン情報 __version__ = "0.1.0"
    - 主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイル（.env, .env.local）および OS 環境変数から設定を自動読み込み（プロジェクトルート推定: .git または pyproject.toml を探索）
    - 自動読み込みを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
    - .env パーサ実装 (_parse_env_line)：
      - コメント、export 先頭指定、シングル/ダブルクォート、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱いに対応
    - .env 読み込みの上書き/保護ロジック（override / protected）を実装
    - Settings クラス：
      - J-Quants / kabu / Slack / DB パス / 環境 (development/paper_trading/live) / ログレベル設定等のプロパティ
      - env/log_level のバリデーション
      - is_live / is_paper / is_dev のユーティリティ

- データ取得・保存（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装
    - レート制限 (120 req/min)：固定間隔スロットリング RateLimiter を採用
    - 再試行ロジック（指数バックオフ、最大 3 回）、408/429/5xx を考慮
    - 401 発生時の自動トークンリフレッシュ（1 回のみリトライ）
    - ページネーション対応の fetch_* 関数（daily quotes / financial statements / market calendar）
    - DuckDB への保存用関数（save_daily_quotes / save_financial_statements / save_market_calendar）
      - idempotent な保存（ON CONFLICT DO UPDATE）を採用
    - データ型変換ユーティリティ (_to_float / _to_int)
    - 取得時の fetched_at を UTC で記録（Look-ahead バイアスのトレーサビリティ確保）

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードから記事を収集して raw_news に保存する処理
    - 記事 ID を URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保
    - defusedxml を用いた XML 安全パース
    - URL 正規化（スキーム・ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）
    - 受信サイズ制限（MAX_RESPONSE_BYTES）・HTTP スキーム検証等の安全対策
    - バルク INSERT のチャンク処理（_INSERT_CHUNK_SIZE）

- 研究用 / ファクター計算
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率の計算（DuckDB SQL を活用）
    - calc_volatility: ATR(20), 相対 ATR (atr_pct), 20日平均売買代金、出来高比率
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算
    - 各関数は prices_daily / raw_financials のみを参照し、本番発注系にはアクセスしない設計
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算
    - rank / factor_summary: ランク変換、統計サマリ（count/mean/std/min/max/median）
    - 外部ライブラリに依存しない純 Python 実装

- 戦略（特徴量エンジニアリング＆シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - build_features(conn, target_date)
      - research モジュールから生ファクター (calc_momentum/calc_volatility/calc_value) を取得
      - ユニバースフィルタ（最低株価・平均売買代金）を適用
      - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 にクリップ
      - features テーブルへ日付単位の置換（DELETE → INSERT のトランザクションで原子性を確保）
      - ルックアヘッドバイアス防止の考慮（target_date 時点のデータのみ使用）
  - src/kabusys/strategy/signal_generator.py
    - generate_signals(conn, target_date, threshold=0.6, weights=None)
      - features と ai_scores を統合して各銘柄の component スコア（momentum/value/volatility/liquidity/news）を算出
      - シグモイド変換や欠損値の中立補完（0.5）を行い final_score を算出
      - デフォルト重みを用い、ユーザ指定 weights は検証・正規化（未知キー・非数値は無視、合計が 1.0 に再スケール）
      - Bear レジーム判定（ai_scores の regime_score 平均が負の場合に BUY を抑制）
      - BUY シグナル（threshold 以上）と SELL（stop_loss / score_drop）を生成
      - SELL 優先ポリシー：SELL 対象は BUY から除外し、BUY ランクを再付与
      - signals テーブルへ日付単位の置換（トランザクション、バルク挿入）
    - _generate_sell_signals: 保有ポジションのエグジット判定（ストップロス -8% 等）

- パッケージエクスポート
  - src/kabusys/strategy/__init__.py
    - build_features, generate_signals を公開

### 変更 (Changed)

- （初回リリースのため該当なし）

### 修正 (Fixed)

- （初回リリースのため該当なし）

### セキュリティ (Security)

- news_collector で defusedxml を採用し XML 系攻撃を低減
- news_collector で受信バイト数上限・HTTP スキーム検査・トラッキング除去など SSRF/DoS 対策を考慮
- jquants_client の HTTP リトライで Retry-After を尊重（429 の場合）

### ドキュメント / 設計ノート

- 各モジュールに詳細な docstring が付与されており、設計方針（ルックアヘッドバイアス防止、冪等性、外部依存回避など）と処理フローが明記されています。
- research モジュールは pandas 等に依存せず標準ライブラリ＋DuckDB SQL で完結する設計です。
- DuckDB への書き込みは原子性（トランザクション）と冪等性（ON CONFLICT）を重視しています。

### 既知の制限 / TODO

- signal_generator のエグジット条件でトレーリングストップや時間決済（保有 60 営業日超）については未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の詳細な SSRF 判定（IPブロックリストなど）は明記されているが実装の詳細はコード提供範囲内でのみ推測可能。
- データベーススキーマ（テーブル定義）は CHANGELOG 範囲に含まれていないため、実運用時はスキーマ整備が必要。
- 単体テスト／統合テストの有無はコードからは判断できないため、テストカバレッジの整備が推奨されます。

---

参考: この CHANGELOG はソースコード中の docstring、関数名、コメントおよび実装から推測して作成しています。実際のリリースノート作成時は、実装者による検証・追記を行ってください。