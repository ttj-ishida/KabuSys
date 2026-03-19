# CHANGELOG

すべての注記は Keep a Changelog の慣習に従います。  
バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

## [0.1.0] - 2026-03-19

### Added
- 初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装。
- パッケージエントリポイントとバージョン定義（src/kabusys/__init__.py）。
- 環境設定管理（src/kabusys/config.py）:
  - .env/.env.local の自動ロード（プロジェクトルートは .git / pyproject.toml で検出）。
  - export 形式・クォート・インラインコメント対応の堅牢な .env パーサー。
  - OS 環境変数保護（.env.local は上書き、OS 環境は保護可能）。
  - 必須変数チェック（_require）と各種設定プロパティ（J-Quants, kabu API, Slack, DB パス, env, log level）。
- データ収集・保存モジュール（src/kabusys/data/*）:
  - J-Quants API クライアント（jquants_client.py）:
    - 固定間隔の RateLimiter（120 req/min）実装。
    - リトライ（指数バックオフ、最大 3 回）、429 の Retry-After 優先、401 時の自動トークンリフレッシュ。
    - ページネーション対応 fetch_* 関数（株価・財務・カレンダー取得）。
    - DuckDB へ冪等保存する save_* 関数（ON CONFLICT/DO UPDATE を想定した実装）。
    - API 呼び出し結果の fetched_at を UTC で記録（ルックアヘッドバイアスのトレースを支援）。
  - ニュース収集モジュール（news_collector.py）:
    - RSS フィード取得・パース（defusedxml 利用）、URL 正規化（トラッキングパラメータ除去）、記事 ID の SHA-256 ベース生成、受信バイト制限、バルク挿入チャンク処理。
- リサーチ関連（src/kabusys/research/*）:
  - ファクター計算（factor_research.py）:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、出来高関連）、Value（PER/ROE の計算）を DuckDB の prices_daily / raw_financials を参照して算出。
    - 欠損・データ不足時の安全な None ハンドリング（ウィンドウサイズ未満は None）。
  - 特徴量探索ユーティリティ（feature_exploration.py）:
    - 将来リターン calc_forward_returns（複数ホライズン対応、入力検証）。
    - スピアマン IC 計算 calc_ic（ランク変換、ties の平均ランク処理）。
    - factor_summary（count/mean/std/min/max/median の統計サマリー）。
    - rank（同順位は平均ランク、丸めによる ties 検出対策）。
  - re-export（src/kabusys/research/__init__.py）で主要ユーティリティを公開。
- 戦略層（src/kabusys/strategy/*）:
  - 特徴量エンジニアリング（feature_engineering.build_features）:
    - research の生ファクターを取得して統合。
    - 株価・流動性によるユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）。
    - 指定カラムの Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位の置換（トランザクションで原子性を担保）。
  - シグナル生成（signal_generator.generate_signals）:
    - features と ai_scores を統合して各コンポーネント（momentum/value/volatility/liquidity/news）スコアを計算。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - final_score に基づく BUY シグナル（閾値デフォルト 0.60）と SELL（ストップロス -8%、スコア低下）を生成。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル閾値以上で BUY 抑制）。
    - signals テーブルへ日付単位の置換（トランザクションで原子性を担保）。
  - strategy パッケージ公開（build_features / generate_signals）。

### Changed
- 初版なので既存リリースからの変更点はなし。設計方針や関数 API に関するドキュメントストリングを多用して実装意図を明確化。

### Fixed
- 初版リリースのため修正履歴なし。ただし実装にはエラー処理・警告出力（logger.warning）を多用して堅牢性を向上。

### Security
- ニュースパーサーで defusedxml を利用し XML 攻撃（XML Bomb 等）対策を実施。
- RSS URL 正規化でスキーム検証やトラッキングパラメータ除去を実装（SSRF 対策の準備）。
- .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化が可能（テスト時の安全策）。

### Performance
- J-Quants クライアントは固定間隔のレートリミッタを実装して API レート制限に適合。
- DuckDB へのバルクインサートを用い、トランザクションでまとめて処理することでオーバーヘッド削減。
- calc_forward_returns 等はホライズンの最大値に基づきスキャン範囲を制限してパフォーマンスを最適化。

### Notes / Known limitations
- positions テーブルに peak_price / entry_date 等がないため、トレーリングストップや時間決済の一部ロジックは未実装（signal_generator 内で注記あり）。
- news_collector の RSS ソースはデフォルトで Yahoo Finance のビジネスカテゴリのみ登録。ソース拡張は容易に可能。
- 一部の SQL 文は DuckDB を前提に記述（ウィンドウ関数や ROW_NUMBER 等を使用）。他の DB では動作しない可能性あり。
- J-Quants API のエラーハンドリングは一般的ケースを想定。実運用では追加の監視とメトリクス収集を推奨。

---

今後の予定（例）
- AI スコア生成パイプラインの実装および ai_scores 連携強化。
- execution 層（kabu ステーション API 経由の注文発行）との統合テスト・安全弁の追加。
- ニュースの銘柄紐付け（news_symbols テーブルへの実装）と自然言語処理向け前処理の高度化。

以上。必要であれば各モジュールごとの詳細な変更履歴（コミット単位想定）やリリースノート文言の微調整を作成します。