# Changelog

すべての変更は Keep a Changelog の形式に従って記録しています。  
安定版リリース以降の互換性ポリシーはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-19

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しています。以下はコードベースから推測できる主要な追加点・設計上の特徴です。

### 追加 (Added)
- パッケージ基盤
  - パッケージ識別子と公開 API を定義（src/kabusys/__init__.py）。
  - __version__ = "0.1.0" を設定。

- 環境設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルまたは OS 環境変数から設定を読み込む自動ロード機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグをサポート。
  - 独自の .env パーサを実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理（クォート有無での挙動差分）など。
  - Settings クラスを提供（プロパティ経由で必須/任意設定値を取得）:
    - J-Quants / kabu API / Slack / DB パス / システム環境（KABUSYS_ENV） / LOG_LEVEL の検証・既定値。
    - is_live / is_paper / is_dev のヘルパープロパティ。

- データ取得・保存（J-Quants）(src/kabusys/data/jquants_client.py)
  - J-Quants API クライアント実装:
    - 固定間隔レートリミッタ（120 req/min）を実装。
    - リトライ戦略（指数バックオフ、最大3回、408/429/5xx を対象）。
    - 401 受信時にはリフレッシュトークンで自動的にトークンを更新して 1 回リトライ。
    - ページネーション対応でデータを全件取得。
    - 取得時刻 (fetched_at) を UTC で記録し、look-ahead bias を意識した設計。
  - DuckDB へ保存するユーティリティ（冪等性を確保）:
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT で更新。
    - PK 欠損行はスキップしログ出力。
    - 型変換ユーティリティ (_to_float / _to_int)。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集し raw_news に保存する機能。
  - セキュリティ・堅牢性対策:
    - defusedxml を用いた XML 解析（XML Bomb 等に対処）。
    - HTTP/HTTPS スキーム以外を拒否、受信サイズ上限（MAX_RESPONSE_BYTES）を設定。
    - トラッキングパラメータ（utm_* 等）の除去と URL 正規化機能。
    - 記事 ID を URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - バルク INSERT のチャンク化、トランザクションの利用、挿入数計測。

- リサーチ・ファクター計算 (src/kabusys/research/)
  - factor_research.py:
    - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）、Volatility（atr_20 / atr_pct）、Value（per / roe）、
      Liquidity（avg_turnover / volume_ratio）などファクター計算関数を実装。
    - DuckDB のウィンドウ関数を用いた効率的な SQL ベース計算。
    - データ不足時は None を返す安全設計。
  - feature_exploration.py:
    - 将来リターン計算 (calc_forward_returns)：複数ホライズン（デフォルト 1,5,21）に対応。
    - IC（Information Coefficient）計算 (calc_ic)：Spearman（ランク相関）を計算する実装。
    - 統計サマリー (factor_summary) とランク付けユーティリティ (rank)。
  - research パッケージの公開 API を定義（zscore_normalize も re-export）。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールからの生ファクターを統合して features テーブルを構築するパイプラインを実装。
  - ユニバースフィルタ（最低株価300円、20日平均売買代金5億円）を適用。
  - 指定列を Z スコア正規化し ±3 でクリップ。結果を features テーブルへ日付単位の置換（トランザクション + バルク挿入で原子性）。
  - ルックアヘッドバイアス対策（target_date 時点のデータのみ使用）。

- シグナル生成エンジン (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成。
  - コンポーネントスコア実装:
    - momentum / value / volatility / liquidity / news（AIスコアの変換）を計算する関数群。
    - sigmoid を用いた 0..1 変換、欠損は中立 0.5 で補完。
  - 重み（デフォルトは momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）を受け取り妥当性チェックと正規化を行う。
  - Bear レジーム判定（AI の regime_score の平均が負かつ十分なサンプル数で判断）により BUY を抑制。
  - エグジット（SELL）条件:
    - ストップロス（終値ベースで -8% 以下）
    - final_score が閾値未満
    - （未実装だが設計にトレーリングストップ / 時間決済が言及）
  - signals テーブルへ日付単位の置換（トランザクションで原子性を保証）。
  - generate_signals は features が空の場合でも SELL 判定は行う設計。

- strategy パッケージ公開 API（build_features, generate_signals）を定義。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector で defusedxml を利用し XML の安全な解析を実装。
- ニュース収集で受信サイズ上限を設け、SSRF 対策（スキーム検証）・トラッキングパラメータ除去を実施。
- J-Quants クライアントでリトライ/トークンリフレッシュを制御し、誤った 401 ハンドリングによる無限ループを回避。

### 既知の制限 / TODO（コードから推測）
- signal_generator の一部のエグジット条件（トレーリングストップ、時間決済）は positions テーブルに追加情報（peak_price / entry_date 等）が必要で未実装。
- execution パッケージは空（発注ロジック・kabu API 統合は別途実装が必要）。
- 一部の統計/解析は pandas 等を使わず標準ライブラリで実装しているため、非常に大規模データでの性能チューニング余地あり。

### 互換性 (Backwards Compatibility)
- 初回リリースにつき破壊的変更はなし。

---

貢献・バグ報告・改善提案はリポジトリの issue/PR を通してお願いします。