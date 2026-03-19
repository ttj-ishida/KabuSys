# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

なお本CHANGELOGはリポジトリ内のソースコードから機能・設計を推測して作成しています。

## [Unreleased]

### Added
- なし

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-03-19

最初の公開バージョン。日本株自動売買システムのコア機能群を実装。

### Added
- パッケージ構成
  - kabusys パッケージの基本エントリポイント（src/kabusys/__init__.py、バージョン `0.1.0`）。
  - サブモジュールの外部公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - 強化された .env パーサ（export KEY=val 形式対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント処理）。
  - 必須環境変数取得 _require() と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境種別・ログレベルなど）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と便利なプロパティ（is_live / is_paper / is_dev）。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（fetch_* 系のページネーション対応関数を含む）。
  - レート制限管理（固定間隔スロットリング _RateLimiter、デフォルト 120 req/min）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx をリトライ対象）。
  - 401 発生時は自動でリフレッシュトークンから id_token を再取得して 1 回リトライ（トークンキャッシュをモジュールレベルで保持）。
  - データ整形ユーティリティ（_to_float / _to_int）と DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）。いずれも ON CONFLICT DO UPDATE により重複更新を排除。
  - fetched_at を UTC ISO8601 で記録し、データ取得時刻のトレーサビリティを確保。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード収集機能（デフォルトで Yahoo Finance のビジネスカテゴリを登録）。
  - 記事ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保。
  - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - セキュリティ対策: defusedxml を利用した XML パース、受信サイズ上限（MAX_RESPONSE_BYTES）によるメモリDoS対策、HTTP/HTTPS のみ許可など（設計理念を明示）。
  - bulk insert のチャンク化、トランザクションでのまとめ保存、INSERT RETURNING 相当を利用して挿入数を正確に扱う方針。

- リサーチ（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: mom_1m / mom_3m / mom_6m、200日移動平均乖離率（ma200_dev）。
    - ボラティリティ/流動性: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率。
    - バリュー: PER, ROE（raw_financials から target_date 以前の最新値を使用）。
    - DuckDB のウィンドウ関数を活用した効率的な実装。データ不足時は None を返す設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns: LEAD を活用して複数ホライズンをまとめて取得）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンランク相関を実装、サンプル数不足時は None）。
    - ファクター統計サマリー（factor_summary）とランク化ユーティリティ（rank）。
    - 外部依存を避け、標準ライブラリのみで実装する設計方針を反映。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research モジュールで計算した raw ファクターをマージして features テーブルに保存する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
  - 正規化: 指定列を Z スコア正規化し ±3 でクリップ（zscore_normalize を利用）。
  - 日付単位での置換アップサート（DELETE → INSERT のトランザクションで原子性を保証）。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を組み合わせた最終スコア final_score を計算し、BUY/SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news（AIスコアをシグモイド変換して news として扱う）。
  - 重みのマージ・検証・再スケーリングロジック（デフォルト重みは StrategyModel.md に基づく）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負の場合。ただしサンプル数が閾値未満なら Bear 判定しない）。
  - BUY シグナル閾値（デフォルト 0.60）。Bear レジームでは BUY シグナルを抑制。
  - SELL ロジック（ストップロス -8% を最優先、次に final_score が閾値未満でのクローズ）。
  - signals テーブルへの日付単位置換（トランザクション + バルク挿入で原子性を保証）。
  - 保有銘柄の価格欠損時には SELL 判定をスキップする安全措置、features に存在しない保有銘柄は score=0.0 扱いで SELL 対象にする挙動。

- パブリック API エクスポート
  - src/kabusys/strategy/__init__.py で build_features, generate_signals を公開。
  - src/kabusys/research/__init__.py で主要な research 関数と zscore_normalize を公開。

### Security
- RSS の XML パースに defusedxml を採用して XML Bomb 等の攻撃を抑止。
- news_collector にて受信サイズ制限や URL 正規化（トラッキングパラメータ除去）を実装し、SSR F や情報漏洩リスクを軽減。
- J-Quants クライアントでトークンの安全な再取得とキャッシュ、HTTP エラーハンドリングを厳密に実装。

### Performance / Reliability
- DuckDB への一括挿入は executemany / トランザクションで効率と原子性を確保。
- J-Quants API 呼び出しは固定間隔スロットリングでレート制限を厳守。
- 再試行（指数バックオフ）と 429 の Retry-After を尊重する実装により外部 API 呼び出しの堅牢性を向上。
- build_features / generate_signals などは冪等設計（date 単位の削除→挿入）で再実行可能。

### Known issues / TODO
- signal_generator のいくつかのエグジット条件は未実装（以下は将来的に実装予定）
  - トレーリングストップ（peak_price の追跡が positions テーブルに必要）
  - 時間決済（保有日数ベースの自動クローズ）
- execution（発注）レイヤーは空のパッケージとして存在するが、発注 API 連携の実装はこのリリースでは含まれない。
- monitoring モジュールも __all__ に含まれているが、実体はこのリリースに含まれていない（将来的な追加を想定）。
- news_collector の一部実装（RSS フィードの詳細パースやシンボル紐付け処理など）は設計のみで、外部統合の追加作業が必要。

### Requirements / Dependencies
- DuckDB Python バインディング（DuckDB 接続を利用するため必須）。
- defusedxml（RSS パースのため）。
- 標準ライブラリの urllib / json / datetime / math など多数を利用。

---

今後のリリースでは execution 層の発注統合、monitoring 実装、未実装のエグジットロジック追加、より詳細なテスト／CI の充実を予定しています。