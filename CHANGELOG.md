# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

全般なポリシー:
- バージョン番号は semver を想定します。
- 日付はリリース日を示します。

## [Unreleased]

## [0.1.0] - 2026-03-19
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期化を追加（kabusys.__version__ = 0.1.0、公開 API の __all__ を定義）。
  - モジュール分割: data, research, strategy, execution, monitoring（execution/monitoring はプレースホルダ）。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動ロードする機能を実装。読み込み優先順位は OS 環境 > .env.local > .env。
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を探索）。これにより CWD に依存しない自動ロードを実現。
  - .env パーサーの実装:
    - コメント・空行スキップ、export KEY=val 形式対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなしでのインラインコメント処理（直前が空白/タブの場合に # をコメント扱い）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスでアプリケーション設定をプロパティとして提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パスなど）。
  - env/log_level のバリデーション（許容値のチェック）を実装。
  - duckdb/sqlite のデフォルトパス設定を含む。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限制御（固定間隔スロットリング）を実装（120 req/min を想定）。
  - 再試行ロジック（指数バックオフ、最大 3 回）と HTTP ステータス処理（408/429/5xx のリトライ処理）。
  - 401 受信時のリフレッシュトークン自動更新（1 回のみ）とキャッシュ化。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を追加。ON CONFLICT を使って更新を行う。
  - 入力変換ユーティリティ (_to_float, _to_int) を実装し、不正値に対して安全に None を返す。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集機能を実装。デフォルトで Yahoo Finance のビジネスカテゴリを指定。
  - URL 正規化機能（トラッキングパラメータ除去、クエリのソート、スキーム/ホスト小文字化、フラグメント除去）。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等の防止）。
    - 受信サイズ上限（10 MB）。
    - 不適切なスキームや SSRF を防ぐための URL 検証を想定（コード内に注意点）。
  - 記事 ID の生成方針（正規化 URL の SHA-256 ハッシュ先頭など）をドキュメント化。
  - raw_news への冪等保存戦略（ON CONFLICT DO NOTHING）やバルク挿入のチャンク処理を設計。

- リサーチ機能（kabusys.research）
  - ファクター計算・探索モジュールを提供。
  - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離の計算を実装（窓不足時は None）。
  - calc_volatility: 20 日 ATR / 相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
  - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を計算（最新の財務レコードを取得）。
  - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得する機能。
  - calc_ic: Spearman のランク相関（Information Coefficient）計算の実装（結合・None 除外・最小サンプルチェック）。
  - rank / factor_summary: ランク付け（同順位は平均ランク）、基本統計量（count/mean/std/min/max/median）を実装。
  - すべて DuckDB 接続を受け取り prices_daily / raw_financials を参照する純粋な分析 API として実装（本番口座や発注 API にはアクセスしない設計）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装:
    - research モジュールの calc_momentum/calc_volatility/calc_value を呼び出して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化して ±3 でクリップ（kabusys.data.stats の zscore_normalize を利用）。
    - features テーブルへ日付単位で置換（DELETE + INSERT をトランザクションで実行し冪等性を確保）。
    - 休場日や当日欠損を考慮して target_date 以前の最新価格を参照。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.6, weights=None) を実装:
    - features と ai_scores を統合してモメンタム／バリュー／ボラティリティ／流動性／ニュース コンポーネントを計算。
    - コンポーネント値をシグモイド変換して重み付き合算により final_score を算出（既定重みを定義）。
    - weights パラメータの入力検証（既知キーのみ、非数値や負値を排除、合計を 1 に正規化）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）。Bear 時は BUY を抑制。
    - BUY シグナルは threshold を超える銘柄、SELL は保有ポジションに対するストップロス（-8%）やスコア低下（threshold 未満）で判定。
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクは再付与。
    - signals テーブルへ日付単位で置換（冪等）。

### Changed
- この初回リリースでは過去の変更点はありません（初版の追加一覧のみ）。

### Fixed
- この初回リリースではバグ修正履歴はありません。

### Security
- news_collector で defusedxml を採用し XML パース攻撃対策を実装。
- J-Quants クライアントで 401 時の安全なトークンリフレッシュとリトライ・レート制限を実装し、外部 API 呼び出しでの誤動作を抑制。
- .env 読み込み時に OS 環境変数を保護する protected 引数を使用し、意図しない上書きを防止。

### Known issues / Not implemented
- signal_generator のエグジット条件としてコメントに記載の以下は未実装:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- execution / monitoring パッケージは現時点では未実装（プレースホルダ）。
- news_collector の SSRF/ネットワーク検査は注意点がコード中にあるが、外部実行環境に応じた追加のネットワーク制約の導入を推奨。
- zscore_normalize の実装は kabusys.data.stats に依存（本リリースでは参照のみ）。テストデータでの検証を推奨。

---

開発者向けメモ:
- 自動環境変数ロードはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能です。
- DuckDB 接続を渡す設計になっているため、ユニットテストではインメモリまたはテスト用 DB を用いて簡単に検証できます。
- ロギングは各モジュールに組み込まれており、INFO/DEBUG レベルで処理の追跡が可能です。

（以上）