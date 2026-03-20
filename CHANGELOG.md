# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に従います。  
リリースはセマンティックバージョニングに準拠します。

全般補足:
- 本プロジェクトは DuckDB を主要なデータストアとして利用します。
- 外部依存は最小限に抑えられており、ニュース取得のみ defusedxml を使用します。
- 設計上、ルックアヘッドバイアス防止・冪等性・トランザクション原子性を重視しています。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回リリース。

### Added
- パッケージ基礎
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - 公開 API を定義（kabusys.strategy.build_features / generate_signals 等を __all__ に公開）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を安全に読み込む自動ロードを実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理等に対応。
    - override と protected キーセットの概念で OS 変数の上書きを制御。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得（必須キー取得時に未設定なら ValueError を送出）。
    - J-Quants / kabuAPI / Slack / DB パス / 環境（development/paper_trading/live） / ログレベルの検証を実装。

- データ取得・保存 (kabusys.data)
  - J-Quants API クライアント (jquants_client.py)
    - レート制限（120 req/min）を固定間隔スロットリングで実装（内部 RateLimiter）。
    - リトライ戦略（最大 3 回、指数バックオフ、408/429/5xx を再試行対象）。
    - 401 受信時は自動でリフレッシュトークンから id_token を取得して 1 回リトライ。
    - ページネーション対応の fetch_* 系関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB へ冪等保存する save_* 関数（raw_prices / raw_financials / market_calendar）を実装（ON CONFLICT DO UPDATE）。
    - データ変換ユーティリティ（_to_float / _to_int）の堅牢な実装。
  - ニュース収集モジュール (news_collector.py)
    - RSS フィードから記事収集し raw_news に冪等保存する機能を実装。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性確保。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_* 等）、フラグメント除去、クエリキー順ソート。
    - defusedxml による XML パースで XML 攻撃対策。
    - 受信バイト数上限（10 MB）や SSRF/非標準スキーム拒否などのセキュリティ考慮。
    - バルク挿入をチャンク化して性能・SQL 長対策、INSERT RETURNING による実挿入数計測を想定。

- 研究用モジュール (kabusys.research)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR・相対 ATR・平均売買代金・出来高比率）、Value（PER, ROE）などのファクター計算関数を実装。
    - DuckDB 上の SQL ウィンドウ関数を利用し営業日欠損や窓不足に対応。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンに対するリターンを一度のクエリで効率的に取得。
    - IC 計算（calc_ic）: スピアマンランク相関（ties は平均ランク）を実装。サンプル不足（<3）時は None を返す。
    - ランク関数（rank）: ties を平均ランクで処理し、丸めで ties 検出漏れを防止。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。

- 特徴量作成 (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date)
    - research モジュールから生ファクターを取得し合成・正規化して features テーブルへ日付単位で置換保存（トランザクションで原子性保証）。
    - ユニバースフィルタ（最小株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 数値ファクターは Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）し ±3 でクリップ。
    - 冪等実行（対象日を削除して再挿入）を確実に実装。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算して final_score を生成。
    - デフォルト重みを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）と、ユーザ重みの検証・正規化（非数値・負値は無視し合計を 1.0 に再スケール）。
    - シグモイド変換・欠損補完（None コンポーネントは中立 0.5）により欠損耐性を確保。
    - Bear レジーム検出（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
    - BUY 判定: final_score >= threshold（デフォルト 0.60）。
    - SELL（エグジット）判定を実装（stop loss -8%、final_score が閾値未満）。SELL は BUY より優先し、signals テーブルへ日付単位で置換保存（トランザクション）。
    - 冪等性と原子性を考慮した DB 更新フローを実装。

- 公開インターフェース
  - kabusys.research, kabusys.strategy の __init__ による便利な再エクスポートを追加。

### Changed
- （初版につき該当なし）

### Fixed
- （初版につき該当なし）

### Deprecated
- （初版につき該当なし）

### Removed
- （初版につき該当なし）

### Security
- ニュースパーサで defusedxml を使用し XML 攻撃を防止。
- ニュースの URL 正規化・トラッキングパラメータ除去・受信サイズ制限・スキーム検査により SSRF / DoS リスクを軽減。
- J-Quants クライアントはトークン自動リフレッシュとレート制限を導入し、不正な連続リクエストや認証失敗による障害を軽減。

### Known limitations / TODO
- signal_generator の一部エグジット条件は未実装（コメント記載）:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の INSERT RETURNING による正確な挿入数計測は DB 実装依存。必要に応じ調整の可能性あり。
- execution／monitoring の具象実装は含まれておらず、発注レイヤーや監視機能は今後実装予定。
- 外部依存（duckdb, defusedxml）が環境にインストールされている必要あり。

---

（注）リリース日・バージョンはコードベースの __version__ とファイル作成時点の推測に基づいて設定しています。今後の変更はこのファイルに逐次追加してください。