# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このリポジトリはセマンティックバージョニングに従います。

- リリース日付はコードベースから推測しています。
- 記載内容はソースコードの実装から推測してまとめた変更点・機能説明です。

## [Unreleased]

## [0.1.0] - 2026-03-19

Added
- 基本パッケージ骨格を追加
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py に定義）
  - モジュール分割: data, strategy, execution, monitoring（__all__で公開）

- 環境設定・自動 .env ロード機能（src/kabusys/config.py）
  - .git または pyproject.toml を起点にプロジェクトルートを探索して .env / .env.local を自動読み込み（カレントワーキングディレクトリに依存しない）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォート無しの場合、行内コメント（#）の扱いを適切に処理
  - 読み込み時のオーバーライド制御（.env と .env.local の優先度）と保護キー（OS 環境変数を上書きしない）をサポート。
  - Settings クラスにより必須環境変数を取得（未設定時は ValueError）。
  - 環境値検証:
    - KABUSYS_ENV は development / paper_trading / live のみ有効
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ有効
  - データベースパス用に Path 型プロパティ（duckdb/sqlite）を提供。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API レート制御（120 req/min）を固定間隔スロットリングで実装（内部 RateLimiter）。
  - リトライロジック（指数バックオフ）を実装。対象はネットワーク系および 408/429/5xx。
  - 401 受信時はリフレッシュ（get_id_token）を自動実行して 1 回だけリトライ（無限再帰を防止）。
  - モジュールレベルで id_token をキャッシュ（ページネーション間で共有）。
  - ページネーション対応の fetch_* 関数を提供:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB へ冪等に保存する save_* 関数を提供（ON CONFLICT DO UPDATE）:
    - save_daily_quotes → raw_prices
    - save_financial_statements → raw_financials
    - save_market_calendar → market_calendar
  - 入力整形ユーティリティ: _to_float / _to_int（安全な変換・不正値は None）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード収集の基本機能を実装（デフォルトで Yahoo Finance の Business RSS を定義）。
  - セキュリティと堅牢性：
    - defusedxml を用いた XML パース（XML Bomb 等へ配慮）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ（utm_*, fbclid 等）の除去、フラグメント削除、クエリソート。
    - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成し冪等性を保証。
  - DB 保存はバルクとチャンク化（_INSERT_CHUNK_SIZE）で実行、INSERT RETURNING を用いて実挿入数を精密に把握。

- 研究（research）モジュール（src/kabusys/research/*）
  - calc_momentum / calc_volatility / calc_value（src/kabusys/research/factor_research.py）
    - prices_daily / raw_financials を参照し、モメンタム（1/3/6M, MA200乖離）、ATR（20日）、出来高/売買代金指標、PER/ROE を計算する。
    - データ不足時に None を返す設計。
  - 特徴量解析ユーティリティ（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns（指定ホライズンに対する将来リターン。デフォルト horizons = [1,5,21]）
    - calc_ic: スピアマン順位相関（IC）を計算。サンプル不足（<3）時は None。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクにする安定したランク付け（round(..., 12) による ties 対応）。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュールから生ファクターを取得して統合・正規化（z-score）を行い features テーブルへ UPSERT。
  - ユニバースフィルタ:
    - 最低株価 _MIN_PRICE = 300 円
    - 20日平均売買代金 _MIN_TURNOVER = 5e8（5 億円）
  - 正規化対象カラムの Z スコア化と ±3 でのクリップ（外れ値影響の抑制）。
  - DuckDB トランザクションで日付単位の置換を行い冪等性を保証。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ保存（日付単位の置換で冪等）。
  - デフォルトファクター重みと閾値:
    - weights: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
    - threshold (BUY): 0.60
  - コンポーネントスコア:
    - momentum: momentum_20, momentum_60, ma200_dev をシグモイドして平均
    - value: PER に基づく逆比例スコア（PER=20 => 0.5、PER→0 => 1.0）
    - volatility: atr_pct の Z スコアを反転してシグモイド
    - liquidity: volume_ratio のシグモイド
    - news: ai_score をシグモイド（未登録は中立補完）
  - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。
  - Bear レジーム検知（ai_scores の regime_score の平均が負かつサンプル数閾値以上で判定）により BUY を抑制。
  - SELL 判定（エグジット）:
    - ストップロス: 終値/avg_price - 1 < -8%（最優先）
    - スコア低下: final_score < threshold
    - 一部未実装（トレーリングストップ / 時間決済）はコードに注記あり。
  - signals テーブルへの保存はトランザクションで日付単位置換。

Changed
- ロギングの充実
  - 処理状況（件数、日付、警告）を詳細にログ出力（各モジュールで info/debug/warning を使用）。
- DB 操作を原子化
  - features / signals / raw_* / market_calendar などのテーブル操作は日付単位の削除→挿入をトランザクションで実施し、部分書き込みを避ける。

Fixed
- （初期リリースのため該当なし。実装時に考慮されたエラー/例外処理を反映）
  - HTTP 401/429/5xx やネットワーク例外に対するリトライやトークン更新処理を追加して堅牢性を向上。
  - DuckDB の挿入時に PK 欠損行をスキップし、スキップ件数をログ出力することでデータ品質の可視化を実装。

Security
- RSS パースに defusedxml を採用、受信サイズ制限を実装、URL 正規化で追跡パラメータ除去、SSRF を考慮した URL チェック（コード上に ipaddress/socket 関連の import とチェック処理の準備あり）など、外部データ取り込み時の安全性対策を導入。

Notes / Implementation details（補足）
- 設計方針として、戦略（strategy）および research モジュールは発注 API / 実際の execution 層へ直接依存しない（分離された責務）。
- Look-ahead bias 防止のため、すべての計算は target_date 時点まで（または target_date 以前の最終値）で行うよう注記がある。
- 外部依存を最小限にする設計（research の実装は標準ライブラリ + DuckDB のみ想定）になっている。

今後の予定（想定）
- execution 層の実装（発注 API との統合）
- strategy のパラメータチューニング用の設定・バックテスト機能追加
- news_collector の記事→銘柄マッピング（news_symbols）ロジックの実装拡充
- トレーリングストップ・時間決済などエグジット条件の追加実装

---

脚注:
- 本 CHANGELOG はソースコード実装内容を元に推測して作成しています。実際のリリースノート作成時はコミットログ・PR・設計資料を参照して更新してください。