Keep a Changelog 準拠の CHANGELOG.md（日本語）

すべての重要な変更はこのファイルに記録します。フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
- なし

[0.1.0] - 2026-03-20
Added
- パッケージ初期リリース (kabusys 0.1.0)
- パッケージの公開 API:
  - kabusys.__version__ を導入（"0.1.0"）。
  - パッケージの主要モジュールを __all__ で公開（data, strategy, execution, monitoring）。
  - strategy モジュールで build_features / generate_signals を公開。
- 環境設定管理:
  - 環境変数/.env の自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート検出は .git または pyproject.toml を起点とする（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - OS 環境変数を保護する protected ロジックにより既存値を上書きしない。
  - .env パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理対応、インラインコメントの扱い、キー/値のトリム等。
  - Settings クラスを導入:
    - J-Quants / kabu API / Slack / DB パス / システム環境（env, log_level）などプロパティ経由で取得。
    - env / log_level の値検証（許容値チェック）と補助プロパティ（is_live/is_paper/is_dev）。
- データ収集 / 保存 (src/kabusys/data):
  - J-Quants API クライアントを実装（jquants_client.py）。
    - レート制限制御（固定間隔スロットリング、120 req/min）。
    - 再試行（指数バックオフ、最大 3 回）、408/429/5xx を再試行対象に。
    - 401 時の自動トークンリフレッシュ（1 回だけ）と ID トークンのモジュールキャッシュ共有。
    - ページネーション対応の fetch_* 関数（daily_quotes, financial_statements, market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供（ON CONFLICT / DO UPDATE）。
    - データ変換ユーティリティ (_to_float / _to_int) を実装し不正データを安全に処理。
    - 取得時刻を UTC で記録し Look-ahead バイアス追跡をサポート。
  - ニュース収集モジュールを実装（news_collector.py）。
    - RSS フィード取得・記事整形・正規化・DB への冪等保存のワークフローを実装。
    - URL 正規化 (トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、ソートされたクエリ) を実装。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保。
    - defusedxml を使用して XML 攻撃を軽減、HTTP(S) スキーム以外拒否、受信サイズ制限 (10 MB) を実装。
    - DB 挿入はチャンク化（デフォルト 1000）かつトランザクションで実行。
- 研究用モジュール（research）:
  - ファクター計算基盤（factor_research.py）を追加:
    - モメンタム (mom_1m, mom_3m, mom_6m, ma200_dev)、ボラティリティ/流動性 (atr_20, atr_pct, avg_turnover, volume_ratio)、バリュー (per, roe) を DuckDB の prices_daily / raw_financials から計算。
    - 計算範囲のバッファや欠損ハンドリング、行ウィンドウ集計の実装。
  - 特徴量探索ユーティリティ（feature_exploration.py）を追加:
    - 将来リターン計算 calc_forward_returns（任意ホライズン、データ不足は None）。
    - スピアマンのランク相関に基づく IC 計算 calc_ic（重複順位は平均ランクで処理、サンプル不足時 None を返却）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸めによる ties 対応）。
  - research パッケージの __all__ エクスポートを整備。
- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research の生ファクターを統合して features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ（最低株価 300 円・20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位の置換（DELETE + INSERT）をトランザクションで行い冪等性を保証。
- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して final_score を算出し BUY/SELL シグナルを生成する generate_signals を実装。
    - momentum/value/volatility/liquidity/news の重み付け合算（デフォルト重みを実装。合計が 1 に正規化）。
    - スコア変換ユーティリティ（シグモイド、平均化、欠損補完ルール）。
    - Bear レジーム検知（ai_scores の regime_score の平均が負の場合に BUY を抑制）。
    - 保有ポジションに対するエグジット判定（ストップロス -8%、スコア低下）を実装。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）を実装。
    - 日付単位の置換で signals テーブルへ保存（トランザクション + バルク挿入）。
- ロギングとエラーハンドリング:
  - 各主要処理で情報/警告/デバッグログを追加。
  - DB トランザクション失敗時のロールバックと警告ログを実装。

Changed
- 新規リリースのための設計注記・実装により、DuckDB を主体としたデータパイプライン設計を採用（SQL ウィンドウ関数多用）。

Fixed
- 該当なし（初版のため修正履歴なし）。

Security
- news_collector で defusedxml を利用し XML の脆弱性を軽減。
- news_collector で受信サイズ制限・HTTP スキーム制限により DoS / SSRF 対策を実装。

Deprecated
- なし

Removed
- なし

Notes / Known limitations
- generate_signals の SELL 条件の一部（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。実装予定のため留意。
- research モジュールは外部データフレームライブラリ（pandas 等）に依存しない実装を選択。大規模データ処理ではパフォーマンスチューニングが必要になる可能性あり。
- .env パーサは多くのケースをカバーするが、極端に複雑なシェル構文（複数行クォートなど）は対象外。
- J-Quants クライアントは urllib ベースの実装であり、より柔軟な HTTP 要求（セッション管理 / 接続プール等）が必要な場合は将来の改善候補。

使用例
- 環境設定の取得:
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token
- 戦略処理の実行例（概念）:
  - build_features(conn, date)
  - generate_signals(conn, date)

以上。