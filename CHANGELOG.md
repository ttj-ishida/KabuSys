# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
詳細: https://keepachangelog.com/ja/

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。トップレベルで公開するサブモジュールを `__all__` に定義（data, strategy, execution, monitoring）。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。プロジェクトルート判定は `.git` または `pyproject.toml` を基準に行うため、CWD に依存しない。
  - `.env` と `.env.local` の読み込み順序（OS 環境変数 > .env.local > .env）に対応。`KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化を提供。
  - .env の行パーサ実装（コメント、`export KEY=...`、クォート中のバックスラッシュエスケープ、インラインコメントの処理などを考慮）。
  - 必須設定を取り出す `_require()`、アプリ設定をカプセル化した `Settings` クラスを提供。J-Quants / kabu API / Slack / DB パスなどのプロパティとバリデーションを実装（`KABUSYS_ENV` / `LOG_LEVEL` の許容値検査等）。
  - デフォルトの DB パス（DuckDB / SQLite）を Path 型で返すユーティリティ。

- データ取得・保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装。
  - 固定間隔のレートリミッタ（120 req/min）を実装して API レート制限を順守。
  - 再試行（指数バックオフ）ロジックを実装（最大 3 回、408/429/5xx を対象）。429 の場合は `Retry-After` ヘッダを尊重。
  - 401 受信時はリフレッシュトークンを用いたトークン再取得を 1 回自動で行う仕組みを組み込み。
  - ページネーション対応の fetch 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装。
  - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT DO UPDATE による重複対策、PK 欠損行のスキップ、fetched_at の記録等を実装。
  - 型変換ユーティリティ `_to_float` / `_to_int` を実装。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからの記事収集および正規化の実装（RSS ソースのデフォルトに Yahoo Finance を含む）。
  - URL 正規化機能（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）を実装。
  - 受信サイズ上限、XML パースの安全化（defusedxml）、SSRF を想定したスキームチェック等の安全対策を設計に反映。
  - バルク INSERT のチャンク処理や挿入数の正確な取得を想定した設計。

- リサーチ（研究）モジュール (`kabusys.research`)
  - ファクター計算を行う `factor_research` を実装（momentum / volatility / value）。
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日データ欠如時は None を返す）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（一定ウィンドウ未満は None）
    - calc_value: per, roe（target_date 以前の最新財務データを使用）
  - 特徴量探索ユーティリティ `feature_exploration` を実装。
    - calc_forward_returns: 複数ホライズン（デフォルト 1/5/21）に対する将来リターンを一括で取得。
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）を計算。サンプル不足時は None。
    - factor_summary: カラムごとの基本統計量（count/mean/std/min/max/median）計算。
    - rank: 同順位は平均ランクとするランク付けユーティリティ。
  - research パッケージの公開関数群を __all__ に整備。

- 戦略モジュール (`kabusys.strategy`)
  - 特徴量エンジニアリング (`feature_engineering.build_features`)
    - research の各ファクター計算を呼び出し、銘柄マージ、ユニバースフィルタ（最低株価300円、20日平均売買代金 >= 5億円）を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）後 ±3 でクリップ。
    - features テーブルへ日付単位での置換（BEGIN/DELETE/INSERT/COMMIT のトランザクション処理）により冪等性と原子性を確保。
  - シグナル生成 (`signal_generator.generate_signals`)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付き合算で final_score を算出（デフォルト重みを実装）。
    - sigmoid, 平均補完、欠損処理、スケーリング（weights が合計 1 でない場合の再スケール）等の堅牢性処理を実装。
    - Bear レジーム判定（AI の regime_score 平均が負かつ十分なサンプル数がある場合）により BUY シグナルを抑制。
    - BUY/SELL のルールを実装（SELL: ストップロス -8% / final_score が閾値未満 等）。未実装の条件（トレーリングストップ、時間決済など）はコード内コメントで明示。
    - signals テーブルへ日付単位での置換処理を実装（冪等）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- .env パーサの挙動を詳細に設計（クォート中のバックスラッシュ、export プレフィックス、インラインコメントの扱いなど）し、現実的な .env のケースに対応。
- DuckDB への書き込み処理はトランザクションで保護し、例外発生時にロールバックを試みるように統一（ロールバック失敗時のログ警告あり）。

### セキュリティ (Security)
- ニュース収集で defusedxml を利用し XML 関連攻撃（XML Bomb 等）に対する対策を導入。
- ニュース URL 正規化でトラッキングパラメータ除去やスキーム規約を実装し、SSRF と追跡パラメータの影響を低減。
- J-Quants クライアントでトークン管理（自動リフレッシュ）とレートリミットの厳守、再試行の制御を行い、過負荷やリトライループのリスクを軽減。

### 既知の制約 / 未実装 (Known issues / Unimplemented)
- signal_generator に記載の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブル側の追加データ（peak_price / entry_date 等）を要するため未実装。将来実装予定。
- news_collector の完全な RSS フェッチ処理（ネットワーク取得・パースの上流処理以降）は一部コードが抜粋されているため、実運用前に接続/パース周りの統合テストが必要。
- 外部依存（DuckDB スキーマ／テーブル定義、Slack/kabu/J-Quants の実運用資格情報）は環境設定が必要。

### 開発者向けメモ
- 設定は .env.example を参考に .env を作成して利用すること（`Settings._require` は未設定時に ValueError を送出）。
- 自動 .env ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト実行時に有用）。

---

貢献・バグ報告は Issue を作成してください。