# Changelog

すべての注目すべき変更点は Keep a Changelog の形式で記載します。  
このファイルは初回リリース v0.1.0 の変更履歴をコードベースから推測して作成しています。

リンクや既知の互換性の問題があれば追記してください。

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期構成（kabusys）を追加。
  - src/kabusys/__init__.py にパッケージ情報（__version__ = "0.1.0"）と公開モジュール一覧を定義。

- 環境変数・設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env の行パーサを実装:
    - コメント行・空行無視、`export KEY=val` 対応、シングル/ダブルクォート内のエスケープ対応、インラインコメント処理（スペース/タブ前の `#` をコメント扱い）など。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供（テスト用途）。
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / システム環境（env, log_level）などをプロパティで取得。未設定時は ValueError を投げる必須取得ヘルパーを提供。
  - env と log_level の値検証（許容値の列挙）を実施。

- データ取得・保存クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - 冪等性を考慮したページネーション取得と保存関数（fetch_* / save_*）。
  - HTTP リトライロジック（指数バックオフ、最大3回、408/429/5xx をリトライ対象）。
  - 401 時は自動トークンリフレッシュを行い1回だけ再試行する仕組みを実装（トークンキャッシュをモジュール内で保持）。
  - DuckDB への保存は ON CONFLICT / DO UPDATE を用いて重複更新を回避、fetched_at を UTC で記録してルックアヘッドバイアスを防止。
  - 各種変換ユーティリティ（_to_float / _to_int）を実装し、入力値の堅牢なパースを行う。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード収集と raw_news への冪等保存ロジックを実装。
  - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成して冪等性を確保。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ削除（utm_, fbclid など）、フラグメント削除、クエリパラメータソート。
  - defusedxml を用いた XML パース（XML Bomb 対策）、受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、HTTP/HTTPS スキーム制限などのセキュリティ施策を導入。
  - DB バルク挿入はチャンク処理を行い、トランザクションでまとめて処理。

- 研究用モジュール（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリューの計算（calc_momentum, calc_volatility, calc_value）を実装。
    - mom: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。
    - vol: 20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
    - value: target_date 以前の最新財務データから PER / ROE を計算（raw_financials と prices_daily を参照）。
    - 各関数は DuckDB の SQL を使用して効率的に集計し、データ不足時は None を返す設計。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、統計サマリー（factor_summary）とランク変換ユーティリティ（rank）を提供。
    - calc_forward_returns は複数ホライズン（デフォルト [1,5,21]）を同時に取得。
    - calc_ic は Spearman の ρ（ランク相関）を実装。サンプル不足（<3）や分散ゼロのケースで None を返す。
    - rank は同順位を平均ランクで処理（round(..., 12) による丸めで ties の検出漏れを防止）。
  - research パッケージから主要 API を再エクスポート。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research で算出した生ファクターを取り込み、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）を適用。
  - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップして外れ値の影響を軽減。
  - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT）することで冪等性と原子性を保証。
  - 処理は target_date 時点のデータのみを使用し、ルックアヘッドバイアスを排除する方針。

- シグナル生成（kabusys.strategy.signal_generator）
  - features テーブルと ai_scores を統合して final_score を計算し、BUY/SELL のシグナルを生成して signals テーブルへ書き込む。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news（AIスコア）。
    - momentum: momentum_20/momentum_60/ma200_dev をシグモイド経由で平均化。
    - value: PER の逆数形式によるスコア（PER=20 で 0.5 の振る舞い）。
    - volatility: atr_pct の Z スコアを反転してシグモイド変換。
    - liquidity: volume_ratio をシグモイドで変換。
    - news: ai_score をシグモイドで変換。未登録は中立値で補完。
  - 重み（デフォルトは strategy モデルに基づく値）を受け、入力の検証・無効値はスキップ・正規化（合計が 1 に再スケール）を行う。
  - Bear レジーム判定: ai_scores の regime_score の平均が負かつサンプル数が閾値以上の場合に BUY を抑制。
  - SELL 条件の実装:
    - ストップロス（終値/avg_price - 1 < -8%） — 優先度高。
    - スコア低下（final_score が threshold 未満）。
    - （未実装だが設計にある）トレーリングストップや保有期間による決済は未実装でコメントあり。
  - signals テーブルへの日付単位置換（冪等・原子性確保）。

### Changed
- （初回リリースにつき変更履歴はなし）

### Fixed
- （初回リリースにつき修正履歴はなし）

### Security
- news_collector において defusedxml を採用、受信バイト数制限、HTTP/HTTPS スキーム限定、トラッキングパラメータ除去などで安全性を強化。
- jquants_client はトークン管理・自動リフレッシュやリトライポリシーを備え、ネットワーク障害や認証切れに耐性を持つ。

### Notes / Implementation details
- DuckDB を主要な分析データストアとして利用する設計。各種保存関数は ON CONFLICT/DO UPDATE を使用して冪等化している。
- ルックアヘッドバイアス防止のため、外部データ取得時に fetched_at を UTC で記録し、戦略生成時は target_date 時点の利用可能データのみを参照する方針を明示。
- 一部のロジック（トレーリングストップや時間決済）は未実装で、将来的な拡張ポイントとしてコメントで残されている。
- 研究モジュールは pandas などの外部ライブラリに依存せずに標準ライブラリと DuckDB SQL で実装されているため簡潔かつ配布に適した構成。

### Breaking Changes
- 初回リリースのため、既存の後方互換性問題はなし。

---

上記は提供されたコードベースから推測した CHANGELOG です。実際のリリースノートに合わせて日付修正・機能の追加/削除・既知の問題やマイグレーション手順があれば追記してください。