# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載します。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [Unreleased]
- ドキュメント的な追記や小さな改善は随時追加予定。

## [0.1.0] - 2026-03-20
初期リリース。本リリースでは日本株自動売買システム「KabuSys」のコア機能を実装しました。主要な追加点・設計方針は以下の通りです。

### 追加
- 基盤パッケージ
  - パッケージのメタ情報と公開 API を定義（src/kabusys/__init__.py, __version__ = "0.1.0"）。
  - パッケージ公開関数を整理（strategy, execution, monitoring, data などを __all__ で公開）。

- 設定・環境変数読み込み（src/kabusys/config.py）
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索して決定）。
  - 高度な .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理などに対応）。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを実装し、必須環境変数取得（_require）・型変換・バリデーション（KABUSYS_ENV, LOG_LEVEL 等）を提供。DB パスの Path での解決を提供。

- データ取得・永続化（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（株価日足、財務データ、マーケットカレンダーの取得）。
  - レート制限対応（固定間隔スロットリング _RateLimiter、120 req/min 想定）。
  - 再試行ロジック（指数バックオフ、最大試行回数、429/408/5xx 対応）。429 の場合は Retry-After ヘッダ優先。
  - 401 Unauthorized 時のリフレッシュトークンでの自動トークン更新（1回のリフレッシュリトライを保証）。
  - ページネーション対応（pagination_key を利用）。
  - DuckDB への冪等保存ユーティリティを実装（raw_prices, raw_financials, market_calendar に対する INSERT ... ON CONFLICT DO UPDATE）。
  - レスポンス変換ユーティリティ（_to_float, _to_int）を実装し、型安全に変換。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news テーブルへ冪等保存する基本機能を実装。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除、小文字化）を実装。
  - セキュリティ対策：defusedxml を用いた XML 攻撃対策、受信サイズ制限（MAX_RESPONSE_BYTES=10MB）、HTTP/HTTPS チェック等を想定した実装方針。
  - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭32文字）を用いる方針を明記。

- リサーチ / ファクター計算（src/kabusys/research/*.py）
  - ファクター計算モジュールを実装（calc_momentum, calc_volatility, calc_value）。
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均乖離）を計算。データ不足時は None。
    - Volatility: 20日 ATR、相対ATR (atr_pct)、20日平均売買代金(avg_turnover)、volume_ratio を計算。
    - Value: 最新財務データ（raw_financials）から PER/ROE を算出（EPS 欠損やゼロは None）。
  - 研究用ユーティリティ:
    - zscore_normalize を外部提供（kabusys.data.stats として再公開）。
    - calc_forward_returns（将来リターン計算、horizons デフォルト [1,5,21]、入力検証あり）。
    - calc_ic（スピアマンのランク相関による IC 計算、サンプル閾値 3 件未満は None）。
    - factor_summary（基本統計量: count/mean/std/min/max/median）。
    - rank（同順位の平均ランク処理、丸め対策あり）。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date) を実装:
    - research モジュールから取得した生ファクターをマージ。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8 円）を適用。
    - 指定カラムを Z スコア正規化（_NORM_COLS）し ±3 でクリップ。
    - features テーブルへの日付単位の置換（トランザクション + バルク挿入で原子性確保）。
    - 欠損や外れ値の扱いに注意した実装。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装:
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを算出。
    - 各コンポーネントの補完方針（None を中立値 0.5 で補完）。
    - 統合重みの取り扱い（デフォルト重み _DEFAULT_WEIGHTS、ユーザー重みの検証・正規化・無効値スキップ）。
    - final_score に基づく BUY シグナル生成（閾値 _DEFAULT_THRESHOLD=0.60）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負なら Bear、ただしサンプル数閾値 _BEAR_MIN_SAMPLES を満たす場合のみ）。Bear 時は BUY を抑制。
    - 保有ポジションに対するエグジット判定（stop_loss: -8% 以下、score_drop: final_score < threshold）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）。signals テーブルへの日付単位置換（トランザクションで原子性）。

- API / モジュールの公開整理
  - strategy.__init__ で build_features / generate_signals を公開。
  - research.__init__ で主要関数を再公開。

### 変更（実装方針・品質）
- DB 書き込みは原子性を意識してトランザクション + バルク挿入で実装（features / signals / raw_* / market_calendar）。
- 冪等性を重視（ON CONFLICT DO UPDATE / INSERT ... DO NOTHING を利用）し、再実行可能な処理設計。
- ルックアヘッドバイアス対策：target_date 時点のデータのみを参照するなど、時系列データ取り扱いで安全側に寄せた実装。
- 入力検証とログ出力を強化（weights の不正値、price 欠損時の警告、PK 欠損レコードのスキップ警告など）。
- 外部依存を最小化（research モジュールは標準ライブラリ + duckdb のみで実装する方針を明記）。

### 修正（既知の挙動・注意点）
- save_* 系の関数は PK 欠損行をスキップし、その件数を警告ログで出力します。
- 一部の機能は意図的に未実装または要拡張（下記「既知の制限」を参照）。

### セキュリティ
- news_collector で defusedxml を使用し XML 関連の脆弱性対応を行う方針。
- RSS の URL 正規化・トラッキング除去・スキームチェック・受信サイズ制限等、外部入力の安全性を考慮。
- J-Quants クライアントはタイムアウトや例外ハンドリング、再試行を実装して過度の例外伝播を抑制。

### 既知の制限 / 未実装の機能
- シグナル生成側の未実装事項（コード内コメント参照）:
  - トレーリングストップ（直近最高値からの -10% など）: positions テーブルに peak_price / entry_date の追加が必要。
  - 時間決済（保有 60 営業日超過）: positions に entry_date 等が必要で未実装。
- news_collector の RSS ソースはデフォルトで Yahoo Finance を設定しているが、運用上の追加ソース登録が必要。
- J-Quants クライアントのレート制限は固定間隔スロットリング実装で概ね安全だが、運用状況に応じた調整が推奨される。
- AI（news）スコアが欠如する場合は中立 0.5 で補完する仕様：AI モデル運用時はスコア形式の整合性に注意。

## 追加情報 / 補足
- 本リリースは「研究」→「戦略」→「実行」へと繋ぐための基盤実装を提供します。実際の運用（発注・口座連携・クラウド運用等）は execution / monitoring 層の実装・検証を別途行ってください。
- 各モジュール内の docstring に設計方針や参照すべきドキュメント（StrategyModel.md, DataPlatform.md など）が記載されています。詳細はソース内コメントを参照してください。

---

（今後のリリースではバグ修正や機能追加、運用改善、インターフェース安定化等を本 CHANGELOG に追記します）