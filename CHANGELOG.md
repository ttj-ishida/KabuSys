# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。

全般的な注意:
- 初期リリース (v0.1.0) は内部設計ドキュメント（StrategyModel.md / DataPlatform.md 等）に基づくアルゴリズム実装、DuckDB を利用したデータ保存、外部 API クライアント、および研究用ユーティリティ群を含みます。
- ログ出力や例外ハンドリング、冪等性（ON CONFLICT / 日付単位の置換）などに配慮した実装方針が採られています。

## [0.1.0] - 2026-03-21

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期化 (`src/kabusys/__init__.py`)。バージョン定義と公開モジュール一覧を提供（data, strategy, execution, monitoring）。
  - 空の execution パッケージ初期化子を追加。

- 環境設定 / ロード機能 (`src/kabusys/config.py`)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。プロジェクトルートは .git または pyproject.toml を起点に検出するため、CWD に依存しない。
  - .env のパースロジックを実装（コメント行、export 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの取り扱いなどに対応）。
  - .env 読み込みの優先順位を OS 環境変数 > .env.local > .env とし、OS 環境変数を保護する仕組みを追加（protected set）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - Settings クラスを追加し、J-Quants / kabuAPI / Slack / DBパス / 実行環境 (development/paper_trading/live) / ログレベルなどのプロパティを提供。必須環境変数が未設定の場合は ValueError を送出する `_require` を実装。
  - env / log_level の妥当性チェック（許容値集合）を実装。is_live / is_paper / is_dev の補助プロパティを追加。

- データ取得・保存（J-Quants クライアント） (`src/kabusys/data/jquants_client.py`)
  - J-Quants API クライアントを実装。ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を提供。
  - 固定間隔のレートリミッタ（120 req/min）を実装（_RateLimiter）。
  - HTTP リクエストのリトライ（指数バックオフ、最大試行回数、指定ステータスでのリトライ）と 401 受信時のトークン自動リフレッシュの実装。トークンはモジュールレベルでキャッシュしてページネーション間で共有。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT による冪等保存と、PK 欠損行のスキップ、挿入件数のログ出力を行う。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正な入力に対する安全な処理を行う。
  - 取得日時（fetched_at）を UTC ISO 形式で記録して Look-ahead バイアスのトレースを可能に。

- ニュース収集モジュール (`src/kabusys/data/news_collector.py`)
  - RSS フィードから記事を収集して raw_news 等に保存するためのユーティリティを追加（README 参照の DataPlatform.md 準拠）。
  - セキュリティ対策を複数実装:
    - defusedxml を用いた XML パース（XML Bomb 等への耐性）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）によるメモリ DoS 緩和。
    - URL 正規化（スキーム/ホスト小文字化、追跡パラメータ（utm_*, fbclid 等）除去、フラグメント削除、クエリキーソート）を実装。記事 ID は正規化後 URL のハッシュを想定（docstring に記載）。
    - HTTP/HTTPS スキーム以外の URL を制限して SSRF を抑制。
  - バルク INSERT のチャンク処理やトランザクションまとめによる DB 負荷低減、ON CONFLICT DO NOTHING による冪等性を考慮。

- 研究（Research）モジュール
  - factor_research (`src/kabusys/research/factor_research.py`)
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20日 ATR, atr_pct）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する calc_momentum / calc_volatility / calc_value を実装。
    - DuckDB のウィンドウ関数を活用した効率的な実装。営業日（連続レコード）ベースのホライズン扱いを採用。
  - feature_exploration (`src/kabusys/research/feature_exploration.py`)
    - 将来リターンをまとめて取得する calc_forward_returns を実装（複数ホライズン対応、最大ホライズンに基づく日付範囲最適化）。
    - スピアマンのランク相関（IC）を計算する calc_ic、ランク化ユーティリティ rank、ファクターの統計サマリ factor_summary を実装。
    - 外部依存（pandas 等）を用いず、標準ライブラリのみで動作する設計。
  - research パッケージの __all__ で主要関数を公開。

- 戦略（Strategy）モジュール
  - 特徴量エンジニアリング (`src/kabusys/strategy/feature_engineering.py`)
    - research モジュールで算出した生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用し、選択した数値カラムを Z スコア正規化（zscore_normalize を利用）して ±3 でクリップ。features テーブルへ日付単位で置換（冪等）する build_features を実装。
    - トランザクション制御（BEGIN/COMMIT/ROLLBACK）により原子性を確保。
    - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみを使用する設計。
  - シグナル生成 (`src/kabusys/strategy/signal_generator.py`)
    - features テーブルと ai_scores を統合して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算し、重み付け合算による final_score を算出する generate_signals を実装。
    - デフォルト重みや閾値を定義。weights 引数は妥当性検査・補完・リスケールされる。
    - Bear レジーム検知（ai_scores の regime_score 平均が負）により BUY シグナルを抑制する処理を実装。
    - エグジット判定ロジック（ストップロス -8% / スコア低下）を実装する _generate_sell_signals。価格欠損時は判定をスキップする安全策を含む。
    - BUY と SELL を日付単位で置換（トランザクション＋バルク挿入）して冪等性を維持。SELL 優先で BUY から除外し、BUY のランクを再付与。
    - 最終的に生成されたシグナル数を返却し、ログ出力を行う。
  - strategy パッケージの __all__ で build_features / generate_signals を公開。

### 変更 (Changed)
- なし（初版のため）。

### 修正 (Fixed)
- なし（初版のため）。

### セキュリティ (Security)
- RSS パースに defusedxml を採用、RSS 用 HTTP 応答の最大バイト数を制限、URL 正規化とトラッキングパラメータ除去、HTTP/HTTPS のみ許可等の対策を追加。

### 既知の制限 / TODO
- signal_generator のエグジット条件の一部（トレーリングストップ、時間決済）は未実装。これらは positions テーブルに peak_price / entry_date 等の追加情報が必要。
- news_collector の記事 ID 生成や記事→銘柄マッピング（news_symbols）関係の詳細実装は docstring に言及があるが、この差分に含まれない追加実装が想定される。
- DuckDB スキーマ（テーブル定義）、Slack 通知や実際の発注（execution 層）との連携は別途実装が必要。

### 破壊的変更 (Breaking Changes)
- なし（初版）。

---

今後のリリースでは次のような点を想定しています:
- execution 層の発注ロジックとモニタリングとの統合
- パフォーマンス最適化（大規模データ処理時のメモリ/クエリ最適化）
- テストカバレッジの追加（各モジュールのユニットテスト / 統合テスト）
- 詳細なドキュメント（API リファレンス、運用手順、DB スキーマ）