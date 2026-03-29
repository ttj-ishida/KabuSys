# Changelog

すべての注目すべき変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠しています。  
リリースは semver を使用します。

## [Unreleased]

（今後の変更点をここに記載します）

---

## [0.1.0] - 2026-03-29

初回公開リリース — KabuSys のコア機能を実装しました。以下は主な追加機能・設計方針の要約です。

### Added
- パッケージ基盤
  - パッケージ名: kabusys（src/kabusys）
  - バージョン: 0.1.0

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサを実装（コメント・export プレフィックス・シングル/ダブルクォート・エスケープをサポート）。
  - 環境変数取得ユーティリティ Settings（J-Quants / kabuステーション / Slack / DB パス / システム設定をプロパティで提供）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と便利なブールプロパティ（is_live / is_paper / is_dev）。

- AI モジュール（src/kabusys/ai）
  - news_nlp（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini, JSON Mode）で銘柄ごとのセンチメント（ai_score）を生成して ai_scores に書き込む。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（銘柄ごとに最大 20 件／チャンク）、トークン肥大対策（記事数・文字数のトリム）、レスポンス検証、スコアの ±1.0 クリップ。
    - ネットワークエラー・429・5xx に対する指数バックオフリトライ、フェイルセーフとして失敗時はスキップ継続。
    - テスト容易性のため API 呼び出し箇所は差し替え可能（ユニットテスト用に patch 可能）。

  - regime_detector（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定し market_regime に冪等書き込み。
    - マクロニュース抽出は news_nlp の calc_news_window を利用、LLM は gpt-4o-mini（JSON Mode）で -1〜1 のスコアを期待。
    - API リトライ（最大試行回数、指数バックオフ）、API失敗時はマクロセンチメントを 0.0 にフォールバック。
    - ルックアヘッドバイアスを防ぐ設計（date < target_date 条件など）。
    - DB 書き込み時は BEGIN / DELETE / INSERT / COMMIT の冪等操作を実施、失敗時は ROLLBACK と例外伝播。

- リサーチモジュール（src/kabusys/research）
  - factor_research (calc_momentum, calc_value, calc_volatility)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
    - Value: PER, ROE（raw_financials から最新財務を取得）
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - DuckDB 上で SQL とウィンドウ関数を活用して効率的に計算
  - feature_exploration (calc_forward_returns, calc_ic, factor_summary, rank)
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）
    - IC（Spearman の ρ）計算（ランク化、同順位は平均ランク）
    - 基本統計量（count/mean/std/min/max/median）計算ユーティリティ
  - zscore_normalize を kabusys.data.stats からエクスポート（research パッケージの統合）

- データプラットフォーム（src/kabusys/data）
  - calendar_management（マーケットカレンダー管理）
    - market_calendar を基に営業日判定 API（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を提供。
    - DB 登録値優先、未登録日は曜日（週末）フォールバック。最大探索日数の保護。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル、健全性チェック）。
  - pipeline / etl（ETL パイプライン）
    - ETLResult データクラス（取得数・保存数・品質チェック問題・エラーの集約）を提供。
    - 差分更新・バックフィル方針・品質チェックの設計方針を実装（jquants_client 経由の保存、idempotent 保存、部分失敗時の保護）。
  - jquants_client との連携を想定した実装ポイント（fetch/save のハンドリング）

- パッケージ公開インターフェース
  - src/kabusys/__init__.py により主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開（モジュール構成の起点を提供）。

### Changed
- 初版リリースにつき過去変更はありませんが、以下の設計上の決定を明記します：
  - ルックアヘッドバイアス防止に重点（datetime.today()/date.today() の不意使用を避ける設計）。
  - DuckDB のバージョン依存性に配慮（executemany の空リスト回避、list バインドの互換性回避など）。
  - OpenAI 呼び出しは JSON Mode（厳密な JSON 出力を期待）かつ温度 0、タイムアウト 30 秒で統一。
  - API 呼び出し箇所はテストで差し替え可能なように独立させる（モジュール間のプライベート関数共有を避ける）。

### Fixed
- 初回リリースのため該当なし。

### Security
- 環境変数の自動読み込みはデフォルトで有効だが、テスト目的等で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- .env の読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。既存の OS 環境変数が不意に上書きされないよう配慮。

### Notes / Usage
- OpenAI API キーを必要とする機能（score_news, score_regime）は api_key 引数または環境変数 OPENAI_API_KEY を使用して API キーを解決します。未設定の場合は ValueError を送出します。
- DuckDB 接続を受け取って処理する関数群は、テストやバッチ運用で容易に組み込める設計です。
- AI スコアやレジーム判定は不確実性を伴うため、API 失敗時は安全側のフォールバック（マクロセンチメント=0.0 等）を行い、処理全体の停止を避けます。

---

今後のリリースでは以下を予定しています（例）：
- strategy や execution の実装（注文発注ロジック、backtest 機能）
- 監視（monitoring）モジュールの充実（Slack 通知等）
- jquants_client の具象化とテストカバレッジ強化

変更や不具合を見つけた場合は issue を作成してください。