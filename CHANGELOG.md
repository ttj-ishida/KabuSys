# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングに従っています。

## [0.1.0] - 2026-03-20

初回リリース — 日本株自動売買システム "KabuSys" の基礎機能を追加。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化（src/kabusys/__init__.py）: バージョン情報と主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml を起点）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - .env パーサーの実装: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
  - protected オプションによる OS 環境変数保護（上書き防止）。
  - Settings クラス（settings インスタンス）:
    - J-Quants / kabu API / Slack / DB パス等の設定プロパティ（必須項目は未設定時に ValueError）。
    - env（development/paper_trading/live）と log_level の値検証。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアント実装:
    - レートリミット管理（120 req/min 固定間隔スロットリング）。
    - 再試行（指数バックオフ、最大3回）。408/429/5xx をリトライ対象。429 の場合は Retry-After 優先。
    - 401 受信時は ID トークンを自動でリフレッシュして 1 回リトライ。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（JPX カレンダー）
    - DuckDB への保存関数（冪等性）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
      - INSERT ... ON CONFLICT DO UPDATE を使用して重複排除・更新
    - 変換ユーティリティ: _to_float / _to_int（堅牢なパースと不正値処理）
    - fetched_at を UTC ISO8601 で保存（Look-ahead Bias をトレース可能に）

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集基盤を追加（既定ソースに Yahoo Finance を登録）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）
    - トラッキングパラメータ（utm_*, fbclid など）除去による URL 正規化
    - URL 検査・正規化ユーティリティ（ホスト/スキーム正規化、クエリソート、フラグメント削除）
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保
  - DB へのバルク挿入はチャンク処理、トランザクションまとめ、INSERT RETURNING を想定した設計

- 研究（research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20日ベース）
    - calc_value: per, roe（raw_financials と prices_daily の組合せ）
    - 各関数は DuckDB の prices_daily / raw_financials のみ参照し、(date, code) ベースの dict リストを返す
  - 特徴量探索（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns: 将来リターン（デフォルト horizon=[1,5,21]）
    - calc_ic: スピアマンのランク相関（IC）計算（同順位は平均ランクで処理）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - rank: 同順位処理を含むランク変換ユーティリティ
  - 研究ユーティリティの公開設定（src/kabusys/research/__init__.py）

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date):
    - research モジュールで計算した生ファクターを取得し結合
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE + INSERT、トランザクションで原子性を保証）
    - 処理はルックアヘッドバイアスを防ぐ設計（target_date 時点のデータのみ使用）

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - シグモイド変換・欠損値は中立値 0.5 で補完
    - final_score を重み付き合算（デフォルト重みを提供）し、閾値以上で BUY、エグジット条件で SELL を生成
    - Bear レジーム判定: ai_scores の regime_score 平均が負（サンプル数閾値あり）なら BUY を抑制
    - SELL 条件実装:
      - ストップロス: 終値/avg_price - 1 < -8%（最優先）
      - スコア低下: final_score が threshold 未満
      - 保有銘柄の価格欠損時は SELL 判定をスキップして誤クローズを防止
    - SELL 対象は BUY リストから除外し、ランク再付与（SELL 優先ポリシー）
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）
    - 重みの入力検証: 未知キーや非数値・負値・NaN/Inf を無視し、合計を 1.0 に再スケール

- strategy パッケージのエクスポート（src/kabusys/strategy/__init__.py）
  - build_features, generate_signals を外部公開

### 変更 (Changed)
- （初版のためなし）

### 修正 (Fixed)
- （初版のためなし）

### 既知の制限 / 注意点 (Known issues / Notes)
- シグナルのエグジット条件のうち、以下は未実装（コメントで言及）:
  - トレーリングストップ（直近最高値からの -10%）
  - 時間決済（保有 60 営業日超過）
  - これらを実装するには positions テーブルへ peak_price / entry_date 等の追記が必要
- news_collector の実装はセキュリティ対策を多数組み込んでいるが、実運用前にフィード別の互換性確認（XML 命名空間／content:encoded 等）を推奨
- J-Quants クライアントはネットワーク／API の仕様（レスポンスフォーマット、rate limit の変更）に依存するため、実運用ではモニタリングとログ観察が必要
- settings の必須環境変数が未設定の場合は起動時に ValueError を投げるため、デプロイ前に .env を適切に用意してください

### セキュリティ (Security)
- RSS パーサーに defusedxml を採用、受信サイズ制限・URL 正規化など SSRF/XML 攻撃・DoS 対策を考慮した設計を導入。
- J-Quants クライアントはトークン自動リフレッシュの際に無限再帰を防ぐ設計（allow_refresh フラグ）になっている。

---

今後の予定（例）
- トレーリングストップ・時間決済などエグジットルールの強化
- execution 層（kabu ステーション連携）とモニタリング機能の実装・統合テスト
- ニュースの銘柄紐付け（ニュース → 銘柄マッピング）アルゴリズムの追加
- 単体テスト・統合テストの追加と CI パイプライン整備

もし CHANGELOG に追記してほしい点（例えばリリース日や強調したい変更）があれば教えてください。