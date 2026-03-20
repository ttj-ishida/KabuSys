# Changelog

すべての重要な変更履歴を Keep a Changelog 準拠の形式で記載します。  
このファイルは後方互換性やリリース情報の参照に使用してください。

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- 開発中の変更や追加予定の機能をここに記載します。

---

## [0.1.0] - 2026-03-20

### Added
- 基本パッケージ構成を追加（モジュール: kabusys, data, research, strategy, execution, monitoring）。
  - src/kabusys/__init__.py にバージョン情報と公開モジュール一覧を定義。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env / .env.local を自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）。
    - .env パースの詳細実装（export プレフィックス対応、クォート内エスケープ、インラインコメント処理）。
    - Settings クラスを実装（J-Quants / kabu / Slack / DB パス / 環境 & ログレベルの検証プロパティ）。

- データ取得 / 保存（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（ページネーション対応）。
    - 固定間隔のレートリミッター（120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
    - 401 受信時のトークン自動リフレッシュ（1 回のみ）とトークンキャッシュ。
    - fetch_* 系（daily_quotes, financial_statements, market_calendar）と DuckDB へ冪等保存する save_* 関数。
    - DuckDB への保存は ON CONFLICT を利用して冪等性を確保。
    - 型変換ユーティリティ（_to_float/_to_int）を実装し不正データを安全に扱う。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィード取得・記事整形・raw_news への冪等保存機能を実装。
    - URL 正規化（トラッキングパラメータ除去・小文字化・フラグメント除去・クエリソート）。
    - セキュリティ対策: defusedxml を利用した XML パース、HTTP/HTTPS スキームの検証、受信サイズ上限（10MB）によるメモリ DoS 対策。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を保証。
    - DB バルク挿入のチャンク処理を採用。

- リサーチ用ユーティリティ / ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタム（1m/3m/6m、MA200 乖離）計算（calc_momentum）。
    - ボラティリティ / 流動性指標（ATR20, atr_pct, avg_turnover, volume_ratio）計算（calc_volatility）。
    - バリュー指標（PER, ROE）計算（calc_value）。
    - DuckDB の SQL ウィンドウ関数を活用し、対象日以前の最新データを用いる設計。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、入力検証）。
    - IC（Information Coefficient）計算（calc_ic、Spearman の ρ を実装、サンプル不足時は None を返す）。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）。

  - research パッケージのエクスポートを整備（src/kabusys/research/__init__.py）。

- 特徴量エンジニアリングとシグナル生成（戦略層）
  - src/kabusys/strategy/feature_engineering.py
    - research モジュールから取得した生ファクターをマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへの日付単位アップサート（トランザクションで日付の置換を行い冪等性を担保）。
    - 価格欠損や非有限値の扱いに考慮。

  - src/kabusys/strategy/signal_generator.py
    - 正規化済みファクターと ai_scores を統合して final_score を計算（コンポーネント: momentum/value/volatility/liquidity/news）。
    - デフォルト重み・閾値を定義し、ユーザー指定 weights の検証と正規化（合計が 1 になるようリスケール）。
    - シグモイド変換・None 補間（中立 0.5）を採用し欠損銘柄の不当な降格を防止。
    - Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつサンプル数閾値）により BUY を抑制。
    - SELL 判定（ストップロス -8% または final_score が閾値未満）を実装。保有銘柄価格欠損時は判定をスキップして誤クローズを回避。
    - signals テーブルへの日付単位置換（トランザクション）で冪等性を保証。

- API/モジュールの公開
  - src/kabusys/strategy/__init__.py で主要関数を公開。

### Changed
- なし（初期リリース）。

### Fixed
- なし（初期リリース）。

### Security
- news_collector にて defusedxml を使用し XML パースの安全性を確保。
- news_collector が受信バイト数を制限することで大容量応答による DoS を軽減。
- jquants_client の HTTP 呼び出しでトークン自動リフレッシュと適切なエラーハンドリングを実装し、不正な認証状態からの復旧を容易に。

### Notes / Known limitations
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等が必要で、現バージョンでは未実装（コード内に注記あり）。
- research モジュールは外部ライブラリ（pandas 等）に依存せずに実装されており、パフォーマンスチューニングは今後の課題。
- DuckDB のスキーマ（テーブル定義）や外部依存環境（J-Quants トークン、kabu API、Slack 設定など）は別途用意が必要。

---

[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0