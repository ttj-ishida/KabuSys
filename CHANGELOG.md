Keep a Changelog に準拠した形式で、コードベースから推測した変更履歴を以下に記載します。

全ての重要な変更はセマンティックバージョニング（MAJOR.MINOR.PATCH）に従っています。ここに記載の内容はソースコードの実装・設計コメントから推測してまとめたものです。

## [0.1.0] - 2026-03-20
最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にてパッケージ名とバージョン（0.1.0）を定義し、主要サブパッケージを __all__ で公開。
- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションあり）。
    - export KEY=val 形式、クォート付き値、行内コメント処理などに対応した .env 行パーサを実装。
    - OS 環境変数を保護する protected パラメータを用いた上書きロジックを導入。
    - 必須環境変数取得時に例外を投げる _require() と Settings クラスを提供（J-Quants / kabu / Slack / DB パス / env・log レベル検証など）。
- データ取得・保存関連（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（id token 取得、ページネーション対応、日足・財務・カレンダー取得）。
    - 固定間隔のレートリミッタ（120 req/min）を実装し、リクエスト間隔を自動調整。
    - ネットワークエラーや 408/429/5xx に対するリトライ（指数バックオフ、最大3回）、および 401 時のトークン自動リフレッシュ処理を実装。
    - 取得データを DuckDB に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で保存する save_* 関数を実装（raw_prices, raw_financials, market_calendar）。
    - データ型変換ユーティリティ（_to_float, _to_int）を追加し、不正値は安全に扱う。
- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS 収集モジュールを実装（デフォルトに Yahoo Finance の RSS を登録）。
    - 記事 ID を URL 正規化後の SHA-256（先頭）で生成して冪等性を確保。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、小文字化、フラグメント除去）および応答サイズ制限（MAX_RESPONSE_BYTES）を導入。
    - defusedxml を用いた安全な XML パース、HTTP スキーム検証、SSRF 対策、チャンク化したバルク INSERT を想定した設計。
- 研究（research）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム（1/3/6ヶ月、MA200 乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER/ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の window 関数や LAG/AVG を用いた効率的な SQL ベース計算を採用。データ不足時は None を返す（安全設計）。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ファクター統計サマリー（factor_summary）、ランク関数（rank）を実装。pandas 等の外部依存なしで標準ライブラリ + DuckDB のみで実装。
  - src/kabusys/research/__init__.py にて上記関数群をエクスポート。
- 特徴量生成（feature engineering）
  - src/kabusys/strategy/feature_engineering.py
    - research で計算した raw ファクターを統合・ユニバースフィルタ（最低株価・平均売買代金）適用・Z スコア正規化（zscore_normalize を利用）し、±3 クリップして features テーブルへ日付単位で UPSERT（削除→挿入のトランザクション）を行う build_features() を実装。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用。
- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - 正規化済み features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換保存する generate_signals() を実装。
    - momentum/value/volatility/liquidity/news の重み付け（デフォルト）と任意重みの補完・再スケーリングロジックを提供。無効な重みは警告して無視。
    - シグモイド変換、コンポーネントスコアの欠損補完（中立 0.5）を採用して欠損耐性を確保。
    - 市場レジーム判定（AI の regime_score 平均）により Bear 相場では BUY を抑制するロジックを実装。
    - 保有ポジションに対するエグジット判定（ストップロス -8% およびスコア低下）を実装。トレーリングストップや時間決済は未実装だが設計上言及。
    - signals テーブルへの保存もトランザクションによる日付単位置換で冪等性を担保。
- Strategy パッケージ公開
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。

### Security
- news_collector で defusedxml を使用し XML 関連の攻撃（XML Bomb 等）に対策。
- RSS の URL 正規化とスキーム検証、受信バイト制限で SSRF やメモリ DoS を軽減。

### Reliability / Observability
- jquants_client のレートリミット、リトライ、トークン自動更新により API 呼び出しの堅牢性を向上。
- 各種処理でログ出力（logger）を適切に配置、警告や情報ログにより運用時の診断を支援。
- DuckDB への書き込みは可能な限り冪等操作（ON CONFLICT）を採用し、BEGIN/COMMIT/ROLLBACK で原子性を確保。

### Notes / Design Decisions
- ルックアヘッドバイアス防止のため、全ての計算・シグナル生成は target_date 時点のデータのみを参照する方針。
- 研究系モジュールは本番の発注・外部口座へのアクセスを一切行わない設計。
- 外部依存は最小限に抑え（DuckDB, defusedxml 等）、pandas 等には依存しない方針。
- 一部仕様（トレーリングストップや時間決済など）は設計書（StrategyModel.md 等）で言及されているが実装は保留／未実装。

---

今後の想定追加（コード・設計コメントからの推測）
- ポジション管理の追加情報（peak_price / entry_date）を positions テーブルに保存してトレーリングストップ・時間決済を実装。
- signal → execution 層の統合（実際の発注 API 呼び出し）と注文制御の実装（execution パッケージ）。
- AI スコア生成パイプライン（news の NLP 処理 → ai_scores テーブル投入）の実装と統合。
- CI / テスト補完、より詳細な入力検証・エラーハンドリングの強化。

以上。追加で日付や細かな変更点の追記、別バージョン（Unreleased）の取り扱いが必要であれば指示してください。