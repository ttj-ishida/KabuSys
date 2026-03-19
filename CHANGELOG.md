# Changelog

すべての重要な変更をここに記録します。形式は「Keep a Changelog」に準拠します。  
リリースは逆時系列（最新が上）で並びます。

テンプレート
- Unreleased: 次回リリースで予定している変更
- 各リリース: 追加 (Added) / 変更 (Changed) / 修正 (Fixed) / 非推奨 (Deprecated) / 削除 (Removed) / セキュリティ (Security)

## [Unreleased]
- 将来的な改善案・TODO（例）
  - PBR / 配当利回りなどバリューファクタの追加実装
  - positions テーブルに peak_price / entry_date を持たせ、トレーリングストップや時間決済を実装
  - execution 層の実装（現状はモジュールプレースホルダ）
  - news_collector のフィード追加・エンティティ抽出の精緻化
  - 単体テスト・CI 増強、型注釈の完全適用

---

## [0.1.0] - 2026-03-19

初回リリース。日本株の自動売買システム（KabuSys）のコア機能群を実装しました。主にデータ収集、研究用ファクター計算、特徴量エンジニアリング、シグナル生成、および環境設定周りのユーティリティを提供します。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ定義とバージョンを追加 (__version__ = "0.1.0")。

- 環境変数/設定管理
  - src/kabusys/config.py
    - .env / .env.local 自動読み込み機能（プロジェクトルート判定は .git または pyproject.toml）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサ（export 形式、クォート／エスケープ、インラインコメント処理対応）。
    - _require/Settings クラスによる必須値チェックと型変換（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）。
    - KABUSYS_ENV / LOG_LEVEL の値検証と is_live / is_paper / is_dev 補助プロパティ。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - 固定間隔スロットリングによるレート制限実装（120 req/min）。
    - 冪等性とページネーション対応でのデータ取得関数:
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx の再試行処理）。
    - 401 時のリフレッシュトークン自動更新（1回のみリトライ、トークンキャッシュ）。
    - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）：
      - ON CONFLICT DO UPDATE による冪等保存。
      - fetched_at に UTC タイムスタンプを記録。
      - PK 欠損行のスキップログと件数報告。
    - ヘルパー: _to_float / _to_int の堅牢な変換ロジック。

- ニュース収集（RSS）モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィード取得・記事パース・正規化（デフォルトは Yahoo Finance のビジネス RSS）。
    - defusedxml による安全な XML パース、受信バイト上限（10 MB）設定。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 記事ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。
    - DB バルク挿入のチャンク処理、INSERT の実行件数把握。
    - セキュリティ考慮（SSRF 防止、受信サイズ制限、XML 攻撃対策）。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - Momentum / Volatility / Value 等のファクター計算:
      - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日データの存在チェック）。
      - calc_volatility: 20 日 ATR（atr_20, atr_pct）、avg_turnover、volume_ratio。
      - calc_value: per, roe（raw_financials から target_date 以前の最新を取得）。
    - DuckDB SQL とウィンドウ関数を活用した効率的実装（スキャン範囲バッファ採用、データ欠損扱いの方針明記）。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21] 営業日）で将来リターンを算出。
    - calc_ic: スピアマンランク相関（IC）計算、サンプル数閾値の扱い。
    - factor_summary: count/mean/std/min/max/median の統計サマリ。
    - rank: 同順位は平均ランクで扱うランク変換（round(v,12) による tie 対応）。
    - 標準ライブラリのみでの実装方針（pandas 等に依存しない）。

  - research/__init__.py に主要関数をエクスポート。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py
    - research モジュールで算出した生ファクターを読み込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）適用。
    - 正規化: 指定列（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）を z-score 正規化（kabusys.data.stats の zscore_normalize を利用）、±3 にクリップ。
    - features テーブルへ日付単位での置換（DELETE + INSERT をトランザクションで実行）による冪等性確保。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみ参照。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合し、各コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - コンポーネント計算ロジック:
      - momentum: momentum_20/60 と ma200_dev のシグモイド平均
      - value: PER に基づく 1/(1+per/20) のスケーリング
      - volatility: atr_pct の Z スコアを反転してシグモイド
      - liquidity: 出来高比率のシグモイド
      - news: ai_score のシグモイド（未登録は中立）
    - デフォルト重み・閾値: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10、BUY 閾値 0.60。
    - weights 引数の検証（未知キー/非数値/負値は無視、合計を 1.0 に正規化）。
    - Bear レジーム判定: ai_scores の regime_score の平均が負のとき（サンプル数閾値あり）BUY を抑制。
    - SELL 条件:
      - ストップロス: 終値 / avg_price - 1 < -8%（優先）
      - final_score が threshold 未満
      - 価格が欠損する銘柄は SELL 判定をスキップして誤クローズを防止
      - 未実装: トレーリングストップ、時間決済（要 positions の追加情報）
    - signals テーブルへ日付単位置換で書き込み（冪等）。
    - BUY と SELL の優先ポリシー（SELL 対象は BUY から除外しランクを再付与）。

- strategy/__init__.py で主要 API（build_features, generate_signals）を公開。

### Changed
- N/A（初回リリースのため該当なし）

### Fixed
- N/A（初回リリースのため該当なし）

### Security
- news_collector: defusedxml の採用、受信サイズ制限、HTTP スキーム制約など SSRF/XXE/DoS 対策を実装。
- jquants_client: トークン管理と安全な再試行ロジックを導入。

### Notes / 設計上の重要点
- ルックアヘッドバイアス対策: ほとんどの処理は target_date 以前のデータのみを参照するように設計されています（prices_daily / raw_financials の参照において）。
- 冪等性: DuckDB への挿入は可能な限り ON CONFLICT / 日付単位の DELETE+INSERT で実装し、再実行可能にしています。
- トランザクション: features / signals の更新は BEGIN/COMMIT/ROLLBACK で原子性を確保。ROLLBACK の失敗はログに記録。
- ロギング: 各主要処理はログ出力を行い、異常系は警告/エラーを残します。
- 未実装機能（今後の予定）:
  - execution 層の発注ロジック（kabu API 統合）
  - positions テーブルの拡張（peak_price / entry_date）によるトレーリングストップ等

---

この CHANGELOG はコードベースの実装内容から推測して作成しています。実際のリリースノートとして公開する際は、日付や担当者、リリース手順などを正式な情報で補完してください。