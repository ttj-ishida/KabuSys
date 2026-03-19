# Changelog

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog 準拠です。

現在のリリース履歴:
- 0.1.0 - 2026-03-19

## [0.1.0] - 2026-03-19

初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下は主な追加点と設計上の要点です。

### 追加 (Added)
- パッケージ構成
  - モジュール構成を提供: kabusys (data, strategy, execution, monitoring を公開)
  - バージョン情報: __version__ = "0.1.0"

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - .env パーサーが export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント（クォート外の '#'）等に対応
  - OS 環境変数を保護する protected キー概念により、`.env` による上書きを制御
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス /運用環境 / ログレベル等の取得と妥当性検証をサポート
  - 必須項目未設定時は ValueError を送出する _require ヘルパー

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（認証取得、ページネーション対応）
  - レート制限対応: 固定間隔スロットリングで 120 req/min を尊重する RateLimiter を実装
  - リトライロジック: 指数バックオフ最大 3 回。408/429/5xx をリトライ対象。429 時は Retry-After ヘッダを尊重
  - 401 Unauthorized を検知するとリフレッシュトークンで ID トークンを自動更新して 1 回だけリトライ
  - ページネーション対応で全レコードを収集
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE で保存。fetched_at を UTC ISO8601 で記録
    - save_financial_statements: raw_financials テーブルへ冪等保存（PK: code, report_date, period_type）
    - save_market_calendar: market_calendar テーブルへ冪等保存（取引日 / 半日 / SQ フラグ）
  - 型変換ユーティリティ _to_float/_to_int を提供（変換失敗は None、int 変換で小数部有りは None）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集と raw_news への冪等保存の設計を実装
  - デフォルト RSS ソースに Yahoo Finance のビジネス RSS を追加
  - 安全対策: defusedxml を利用して XML 攻撃を防止、HTTP スキーム検証や受信サイズ上限（10 MB）を設定
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_*, fbclid など）の除去、フラグメント除去、クエリをソート
  - 大量挿入に対するチャンク化（_INSERT_CHUNK_SIZE）とトランザクション最適化の方針
  - 記事IDを URL 正規化後のハッシュで生成（設計注記）

- 研究（research）モジュール
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev を計算。200日未満は None を返す設計
    - calc_volatility: ATR(20) / atr_pct、avg_turnover、volume_ratio を計算。ATR 窓が不十分な場合は None
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS が 0/欠損のとき PER は None）
  - feature_exploration:
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）に対する将来リターンを計算。horizons の妥当性検証あり
    - calc_ic: スピアマンのランク相関（IC）を計算。サンプル < 3 の場合は None
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出
    - rank: 同順位は平均ランクで処理（丸め誤差対策の round により ties 検出を安定化）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールで計算した生ファクターを統合して features テーブルへ保存する build_features を実装
  - ユニバースフィルタ:
    - 最低株価: 300 円
    - 20日平均売買代金 >= 5億円
  - 正規化: zscore_normalize を使い指定カラムを Z スコア正規化し ±3 でクリップ（外れ値の影響抑制）
  - 書き込みは日付単位で一度 DELETE して INSERT（トランザクションで原子性を保証）、処理は冪等

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成する generate_signals を実装
  - コンポーネントスコア:
    - momentum / value / volatility / liquidity / news（AIスコア）
    - Z スコアをシグモイドで [0,1] に変換し、欠損は中立値 0.5 で補完
  - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10（合計 1 に再スケール）
  - BUY 条件: final_score >= デフォルト閾値 0.60（パラメータで変更可）
  - Bear レジーム検出: ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合は BUY を抑制
  - SELL 条件（エグジット）: ストップロス（終値/avg_price - 1 < -8%）および final_score が閾値未満
  - SELL は BUY より優先し、signals テーブルへ日付単位で置換保存（トランザクションで原子性）
  - weights の入力検証機構（未知キーや負値、非数を無視し、合計が 1 に近くなければ再スケール）

### 変更 (Changed)
- （初期リリースにつき該当なし）

### 修正 (Fixed)
- （初期リリースにつき該当なし）

### セキュリティ (Security)
- XML パースに defusedxml を使用（news_collector）
- RSS / URL 正規化・トラッキングパラメータ除去・受信サイズ制限など、外部データ取り込み時の安全対策を導入
- J-Quants クライアントで認証トークンの自動更新を行うが、無限再帰防止のため get_id_token 呼び出し中はトークン更新を許可しない設計

### 既知の制限・注意点 (Known issues / Notes)
- DuckDB の想定スキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar など）が前提です。スキーマ作成は外部で行う必要があります。
- 一部コメントに記載の未実装機能:
  - トレーリングストップや時間決済（positions テーブルに peak_price / entry_date 等が必要）
  - news_collector の記事ID生成等は設計に基づく実装方針が示されていますが、アダプタや細部は利用環境に合わせて調整が必要です。
- ネットワーク呼び出し（J-Quants や RSS）に依存するため、ネットワーク障害時はリトライやログに基づく復旧が必要です。
- 自動 .env ロードはプロジェクトルート検出に依存するため、配布後や CWD が想定と異なる環境では KABUSYS_DISABLE_AUTO_ENV_LOAD による制御を検討してください。

---

将来的なリリースでは詳細なリファクタ、テスト追加、実行（execution）層やモニタリング機能の実装、エンドツーエンドの統合テストなどを予定しています。