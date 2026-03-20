CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本CHANGELOGは提示されたコードベースの内容から推測して作成しています。

Unreleased
----------

### Added
- 実行（execution）層の統合や追加機能（注文送信・ブローカー連携など）の実装予定を明示。
- 売買ロジックの拡張（トレーリングストップ、時間決済など）や position テーブル拡張（peak_price / entry_date の追加）を今後の課題として記載。

### Changed
- —（初版のため変更履歴なし）

### Fixed
- —（初版のため修正履歴なし）

### Known issues / TODO
- トレーリングストップ・保有日数による時間決済は未実装（signal_generator のコメント参照）。
- execution モジュールは空（発注 API への橋渡し実装が未実装）。
- positions テーブルに peak_price / entry_date がないと実装予定の一部エグジット条件を適用できない。

[0.1.0] - 2026-03-20
--------------------

初期リリース — 日本株自動売買システム "KabuSys" の基礎機能を提供。

### Added
- パッケージ化
  - パッケージ名: kabusys、バージョン 0.1.0（src/kabusys/__init__.py にて定義）。
  - サブパッケージ公開: data, strategy, execution, monitoring（__all__ を公開）。

- 設定管理 (src/kabusys/config.py)
  - .env 自動読み込み機能を実装（プロジェクトルートの検出: .git / pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサ: export 形式、クォート内のエスケープ、インラインコメント処理などを考慮した堅牢なパース処理を実装。
  - .env 読み込み時に OS 環境変数を保護する protected 機構。
  - Settings クラスを提供:
    - 必須設定の取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）と未設定時の明確なエラー。
    - KABU_API_BASE_URL のデフォルト値（http://localhost:18080/kabusapi）。
    - データベースパス設定（DUCKDB_PATH, SQLITE_PATH）の Path 化。
    - KABUSYS_ENV / LOG_LEVEL の検証（有効値チェック）とユーティリティ is_live / is_paper / is_dev。

- データ収集・永続化 (src/kabusys/data/)
  - J-Quants クライアント (jquants_client.py)
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
    - リトライ（指数バックオフ、最大 3 回）、HTTP 429 の Retry-After 考慮、ネットワークエラー再試行。
    - 401 受信時にリフレッシュトークンで自動トークン更新（1 回まで）する仕組み。
    - ページネーション対応の取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT による冪等保存）。
    - 型変換ユーティリティ: _to_float / _to_int（柔軟で安全な変換）。
    - fetched_at を UTC ISO フォーマットで記録し、データ取得時点をトレース可能に。

  - ニュース収集 (news_collector.py)
    - RSS フィードからの記事収集機能を実装（デフォルトソースに Yahoo Finance を設定）。
    - セキュリティ対策: defusedxml による XML パース、安全な URL 検証（HTTP/HTTPS のみ）、受信サイズ制限（MAX_RESPONSE_BYTES）。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 記事ID生成は正規化 URL の SHA-256（先頭 32 文字）等を利用して冪等性を保証。
    - DB へのバルク挿入を意識したチャンク処理とトランザクション化の方針。

- リサーチ（研究）モジュール (src/kabusys/research/)
  - ファクター計算 (factor_research.py)
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200 日 MA の乖離）を計算。
    - calc_volatility: atr_20 / atr_pct, avg_turnover（20 日平均売買代金）, volume_ratio を計算。true_range の NULL 伝播を厳密に制御。
    - calc_value: raw_financials から最新財務を取得し per / roe を計算。
    - SQL + DuckDB を活用した実装。外部 API や発注系依存なし。

  - 特徴量探索・統計 (feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンのランク相関（IC）計算（ties を平均ランクで扱う）。
    - factor_summary: count/mean/std/min/max/median を計算する軽量統計関数。
    - rank: 同順位は平均ランクとするランク付けユーティリティ。
    - pandas 等外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

  - research パッケージ公開関数をまとめた __init__（zscore_normalize などのユーティリティ再公開含む）。

- ストラテジー（戦略）モジュール (src/kabusys/strategy/)
  - 特徴量作成 (feature_engineering.py)
    - research モジュールの生ファクターを取得（calc_momentum, calc_volatility, calc_value）。
    - ユニバースフィルタを実装（最低株価 _MIN_PRICE=300 円、20 日平均売買代金 _MIN_TURNOVER=5e8 円）。
    - 指定列を z スコア正規化（zscore_normalize を利用）して ±3 でクリップ。
    - features テーブルへの日付単位の置換（DELETE + INSERT）で冪等性と原子性を確保（トランザクション使用）。
    - 欠損値・異常値のハンドリングとログ出力。

  - シグナル生成 (signal_generator.py)
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を計算。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news の計算ロジックを実装。
      - momentum: momentum_20/momentum_60/ma200_dev をシグモイド平均化。
      - value: PER を 20 を基準に正規化（PER が小さいほど高スコア）。
      - volatility: atr_pct の Z スコアを反転してシグモイド。
      - liquidity: volume_ratio のシグモイド。
      - news: ai_score をシグモイド変換（未登録は中立扱い）。
    - 重み付けの検証と補完（_DEFAULT_WEIGHTS）: ユーザ指定 weights の検証（不正値は無視）、合計が 1 でない場合の再スケール。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数が十分（_BEAR_MIN_SAMPLES）なら BUY を抑制。
    - BUY 生成: final_score >= デフォルト閾値 0.60（Bear 時は抑制）。
    - SELL 生成: 保有ポジションに対してストップロス（-8%）／スコア低下（threshold 未満）で判定。価格欠損時は SELL 判定をスキップして誤クローズを防止。
    - signals テーブルへの日付単位置換（DELETE + INSERT）で冪等性を確保。ROLLBACK の失敗は警告ログ出力。
    - ロギングによる実行記録（INFO/DEBUG/警告）。

### Security
- RSS パーサに defusedxml を使用して XML に対する攻撃（XML Bomb 等）対策。
- ニュース収集での URL 正規化やトラッキングパラメータ除去により意図しない重複や追跡を抑制。
- .env 読み込み失敗時に警告発行、プロセス環境を意図せず上書きしない保護機構あり。

### Reliability / Safety
- DuckDB へのバルク挿入は ON CONFLICT / DO UPDATE を多用して冪等性を確保。
- 各種 DB 更新はトランザクション（BEGIN / COMMIT / ROLLBACK）で原子性を担保。ROLLBACK 失敗時は logger.warning を出力。
- J-Quants クライアントはレート制限とリトライを備え、ページネーションに対応。
- 取得データに fetched_at を付与し、Look-ahead Bias の追跡を容易に。

### Notes / Limitations
- 一部アルゴリズム（トレーリングストップ、時間決済）はコメントで未実装として明示。positions テーブルの拡張が必要。
- execution パッケージは現時点で実装なし。注文実行ロジック・ブローカー連携は次フェーズ。
- research モジュールは pandas 等に依存せず純粋な Python 実装のため、大規模データでのパフォーマンスチューニングは今後の課題。
- モジュールレベルの ID トークンキャッシュは単純実装のため、マルチスレッド/マルチプロセス環境での安全性検討が必要。

References
----------
- 本CHANGELOGはソースコード内の docstring / コメント / 実装内容に基づいて作成しています。コードの詳細実装や将来の変更はソースを参照してください。