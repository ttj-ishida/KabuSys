CHANGELOG
=========

すべての変更は Keep a Changelog の方針に従い記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-03-20
-------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ情報
    - __version__ を 0.1.0 に設定。
    - パッケージ公開 API 用に __all__ を設定（data, strategy, execution, monitoring）。
  - 環境設定/ロード機能 (kabusys.config)
    - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート探索ロジックを実装（.git または pyproject.toml を探索）。
    - .env 解析は export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントを考慮してパース。
    - .env の読み込み優先順位は OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - 必須設定取得ヘルパ (_require) と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 実行環境 / ログレベル等）。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値以外は ValueError）。
  - データ取得・保存 (kabusys.data.jquants_client)
    - J-Quants API クライアントを実装。
    - 固定間隔のレート制限器を実装（120 req/min に対応）。
    - リトライ（指数バックオフ）を実装、対象ステータスやネットワークエラーに対応。最大試行回数の定義あり。
    - 401 に対する自動トークンリフレッシュを実装（リフレッシュは1回のみ、無限ループ防止）。
    - ページネーション対応のデータ取得（daily_quotes / statements / trading_calendar）。
    - DuckDB へ保存する際の冪等処理（ON CONFLICT DO UPDATE）を提供：
      - raw_prices（株価日足）
      - raw_financials（財務データ）
      - market_calendar（取引日情報）
    - 型変換ユーティリティ（_to_float / _to_int）を追加し不正な値を安全に扱う。
  - ニュース収集 (kabusys.data.news_collector)
    - RSS フィード収集の基本実装を追加（既定ソースに Yahoo Finance Business）。
    - URL 正規化（トラッキングパラメータ除去・クエリソート・スキーム/ホスト小文字化・フラグメント除去）。
    - 受信サイズ制限（MAX_RESPONSE_BYTES）や XML パースに defusedxml を使用する等、堅牢性対策を実装。
    - 記事ID は正規化 URL の SHA-256（先頭 32 文字）を使う方針（冪等性確保）。
    - DB 挿入をバルク／チャンク化してパフォーマンスと SQL 長制限に配慮。
  - リサーチ機能 (kabusys.research)
    - ファクター計算群を実装（calc_momentum, calc_volatility, calc_value）。
      - Momentum: 1/3/6 ヶ月リターン、200 日移動平均乖離など。
      - Volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率。
      - Value: PER / ROE（raw_financials から参照）。
    - 特徴量探索ユーティリティを実装（calc_forward_returns, calc_ic, factor_summary, rank）。
      - calc_forward_returns: 複数ホライズン（デフォルト 1,5,21 営業日）に対応。返却は fwd_{h}d カラム。
      - calc_ic: スピアマンランク相関（IC）計算（有効サンプル数チェック）。
      - factor_summary: count/mean/std/min/max/median を計算。
  - 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
    - build_features 実装:
      - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価・平均売買代金）を適用。
      - 指定カラムについて Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）と ±3 でのクリッピングを適用。
      - features テーブルへの日付単位の置換（DELETE + INSERT をトランザクション内で実行）で冪等性を保証。
      - 休場日や当日の欠損に対して target_date 以前の最終価格を参照する実装。
  - シグナル生成 (kabusys.strategy.signal_generator)
    - generate_signals 実装:
      - features と ai_scores を統合し、各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
      - シグモイド変換、欠損値補完（中立値 0.5）、重みのマージ・再スケールロジックを提供（デフォルト重みは StrategyModel.md に基づく）。
      - Bear レジーム判定（AI の regime_score 平均が負の場合。ただしサンプル数閾値あり）。
      - BUY シグナル生成（閾値超過）／SELL（ストップロス、スコア低下）を判定。
      - SELL 優先ポリシー（SELL 対象は BUY リストから除外）、signals テーブルへ日付単位で置換して書き込み（トランザクション）。
    - 売りシグナル: ストップロス（-8%）と final_score が閾値未満の判定を実装。トレーリングストップや時間決済は未実装（要 positions テーブルの拡張）。
  - モジュール設計上の注意点・方針の明示
    - ルックアヘッドバイアスを避けるため target_date 時点のデータのみを使用する方針。
    - 発注/実行層（execution）には直接依存しない戦略／研究 API の設計。
    - 外部ライブラリ依存を抑えつつ（研究で pandas 等に依存しない実装方針）DuckDB を中心に集計を行う。

Fixed
- DB トランザクション処理時の安全策を実装（例: build_features / generate_signals で例外時に ROLLBACK を試行し、ROLLBACK の失敗は警告ログで扱う）。
- API 呼び出しの JSON デコード失敗時に詳細メッセージを返すよう改善（jquants_client._request）。

Security
- RSS XML のパースに defusedxml を採用し XML 関連攻撃を軽減（news_collector）。
- ニュース収集で受信サイズ制限を導入してメモリ DoS を低減（MAX_RESPONSE_BYTES）。
- J-Quants クライアントはトークンリフレッシュ時の再帰（無限ループ）を防止する設計（allow_refresh フラグ・1 回のみリフレッシュ）。

Performance
- J-Quants クライアントで固定間隔レートリミッタを導入、429 の Retry-After を尊重する実装。
- news_collector のバルク挿入をチャンク化して大量データ挿入時のオーバーヘッドを低減。
- リサーチ系クエリはスキャン範囲を制限するために「カレンダーバッファ（日数×倍率）」を利用してパフォーマンスに配慮。

Internal
- 一部ユーティリティで不正や欠損値を安全に扱えるように入力検証とガードを追加（weights の検証、_to_int/_to_float、Z スコア処理の NaN/Inf 対応等）。
- docs/README 等は同梱されていないが、関数コメントと docstring に設計意図・使用例・制約を明記。

Notes / Migration
- 環境変数必須項目:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - データベースパスは DUCKDB_PATH / SQLITE_PATH で上書き可能（デフォルト: data/kabusys.duckdb, data/monitoring.db）
- features / signals / ai_scores / positions 等のテーブル定義は本リリースに含まれない（利用時は事前にスキーマを作成する必要あり）。関数はこれらテーブルの存在を前提とする。

Acknowledgements / Known limitations
- execution パッケージは空のエントリポイントとして存在する（発注周りの実装は次フェーズ）。
- 一部仕様（トレーリングストップ、時間決済など）はコメントで未実装とされており、positions テーブルの拡張が必要。
- news_collector における SSRF 防止のための IP/ホストチェック処理の骨組みは示唆されているが、現状のコード断片では完全な検証ロジック（外部ホストの拒否など）が提供されていない可能性があるため、運用時はネットワーク制限/プロキシ経由での安全対策を推奨。

----

今後の予定
- execution 層（kabuapi を用いた発注ロジック）の実装。
- モニタリング機能（Slack 通知・監視）および運用自動化の強化。
- テストカバレッジの追加と CI ワークフロー整備。