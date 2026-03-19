CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。
既存バージョン: 0.1.0（初期リリース）

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-19
-------------------

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しています。
主にデータ取得／保存、研究用ファクター計算、特徴量生成、シグナル生成、設定管理、ニュース収集まわりの機能が含まれます。

Added
- パッケージ基礎
  - src/kabusys/__init__.py にパッケージ情報（__version__ = "0.1.0"）と公開サブパッケージを定義。
- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装（export 句、クォート処理、インラインコメント処理、上書き制御、保護キー機能）。
  - Settings クラスによる設定アクセスラッパー（J-Quants トークン・kabu API パスワード・Slack トークン・DB パス・実行環境判定等）。
  - env/log level の検証（有効な値チェック）。
- データ取得クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアント実装（ページネーション対応）。
  - API レート制限制御（_RateLimiter、120 req/min 固定間隔スロットリング）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を再試行対象）。
  - 401 受信時の ID トークン自動リフレッシュ（1 回リトライ）とモジュールレベルのトークンキャッシュ。
  - fetch_* 系（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）と DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。保存は冪等（ON CONFLICT / DO UPDATE）で実施。
  - レスポンスパース用の安全な型変換ユーティリティ（_to_float / _to_int）。
- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得と記事整形パイプライン。既定の RSS ソースを提供（Yahoo Finance）。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、クエリソート、フラグメント除去）。
  - 受信サイズ制限（MAX_RESPONSE_BYTES）や XML パースに defusedxml を利用してセキュアに実装。
  - 記事 ID を正規化 URL の SHA-256 ハッシュで生成して冪等保存を目指す設計。
  - DB へのバルク挿入をトランザクションでまとめ、チャンク処理で SQL パラメータ上限に配慮。
- 研究（research）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials のみ参照。
    - モメンタム（1m/3m/6m、MA200 乖離）、ATR ベースのボラティリティ、20 日平均売買代金・出来高比率、PER / ROE を計算。
    - 欠損やデータ不足に対する安全な扱い（必要行数未満は None）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（複数ホライズンで将来リターンを計算）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。
    - 外部依存を用いず標準ライブラリ＋DuckDBで実装。
  - research/__init__.py で主要 API をエクスポート。
- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features 実装：research の calc_* を呼び、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）適用→ Z スコア正規化（±3 クリップ）→ features テーブルへ日付単位の置換（トランザクションによる原子性）。
  - 正規化対象カラムの定義と処理フロー（zscore_normalize を利用）。
  - ルックアヘッドバイアス防止を考慮した実装方針を注記。
- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals 実装：features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのスコアを算出して最終スコア final_score を算出。
  - デフォルト重み・BUY 閾値（0.60）、STOP_LOSS（-8%）等を定義。
  - Bear レジーム判定（ai_scores の regime_score 平均が負なら Bear、最小サンプル数チェック有り）により BUY シグナルを抑制。
  - 保有ポジションに対するエグジット判定（stop_loss / score_drop）を実装。SELL 対象を BUY から除外し、signals テーブルへ日付単位の置換で保存。
  - weights の入力検証（未知キー／非数値／負値を無視、合計が 1.0 になるよう再スケール）。
- strategy/__init__.py で build_features / generate_signals を公開。
- data.stats / research の Z スコア正規化ユーティリティを活用する API をエクスポート。

Changed
- 該当なし（初回リリース）

Fixed
- 該当なし（初回リリース）

Removed
- 該当なし（初回リリース）

Security
- HTTP/XML 周りの安全対策
  - news_collector で defusedxml を使用し XML 関連の攻撃を緩和。
  - news_collector で受信サイズ上限を設けてメモリ DoS の緩和を試みる。
  - fetch / request ロジックで 429 の Retry-After を尊重する実装。
- 環境変数取り扱い
  - 環境変数の読み込みに際して保護キーセット（OS 環境変数）を考慮することで意図しない上書きを防止。

Known limitations / Notes
- 未実装のエグジット条件（feature_engineering / signal_generator 参照）
  - トレーリングストップ（直近最高値から -10%）や時間決済（保有 60 営業日超）については、positions テーブルに peak_price / entry_date が必要であり未実装。
- news_collector の RSS パーサや URL 正規化の一部は現行設計に基づくが、実運用ではさらに多様なフィード形式・エンコーディング対応が必要になる可能性あり。
- J-Quants API クライアントは urllib を利用した実装。高機能な HTTP クライアントを使うと利便性が向上する（未採用の理由：外部依存を抑えるため）。
- DuckDB スキーマ（tables の定義）や実際のデータパイプラインはこのリリースに含まれないため、実行には適切なテーブル定義が必要。

開発・コントリビュート
- 初期実装（初回公開）。今後、ユニットテスト、ドキュメント、エラーハンドリングの強化、運用監視の追加などを予定。

ライセンス / 著作権
- リポジトリ内ファイルに従う（本CHANGELOGはコードから推測して作成したサマリです）。