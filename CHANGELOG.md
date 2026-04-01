# Changelog

すべての重要な変更点は Keep a Changelog のフォーマットに従って記載しています。英語版や個別コミットログではなく、公開 API と動作仕様の観点でコードベースから推測してまとめています。

注意: バージョン番号はパッケージ内の __version__ を参照しています。

本文書の形式:
- Unreleased: 今後の変更（現時点では空）
- 各リリース: 日付・カテゴリ別の要約（Added / Changed / Fixed / Known issues）

---

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-04-01

### Added
- パッケージ初期リリース。モジュール構成と主要機能を実装。
  - パッケージエントリポイント: kabusys.__init__ にバージョン "0.1.0" と主要サブパッケージの公開を追加。
- 環境設定管理 (kabusys.config)
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を起点に探索）。
  - .env / .env.local ファイル自動ロード（優先順位: OS 環境変数 > .env.local > .env）。
  - .env パーサの実装:
    - export KEY=val 形式対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォート有無での差異）
    - 上書き制御（override）と OS 環境変数保護（protected set）
  - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テストで利用可能）。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベルの取得とバリデーションを実装。
    - 必須環境変数 (例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD) は未設定時に ValueError を送出。

- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols から銘柄ごとにニュース記事を集約し、OpenAI (gpt-4o-mini, JSON mode) でセンチメントを算出して ai_scores テーブルへ保存する機能。
    - JSTベースのニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST → UTC での比較に変換）。
    - バッチ処理（最大 20 銘柄/チャンク）、トークン肥大対策（記事数・文字数制限）。
    - 再試行（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分成功時の安全な DB 書き換え（該当コードのみ DELETE → INSERT）。
    - テスト容易性: OpenAI 呼び出しを差し替え可能（内部 _call_openai_api の patch）。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは raw_news からキーワードフィルタで抽出、OpenAI（gpt-4o-mini）に JSON 応答を要求。
    - API エラー時のフェイルセーフ（macro_sentiment = 0.0）、リトライ処理、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト容易性を考慮した API 呼び出し差し替え可能箇所。

- リサーチ機能 (kabusys.research)
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）の計算。
    - calc_volatility: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、出来高比率。
    - calc_value: raw_financials を用いた PER、ROE の算出（最新報告日ベース）。
    - 設計上 DuckDB を用いた SQL ベース実装で、外部 API へは依存しない。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンの計算（LEAD を利用）。
    - calc_ic: スピアマン（ランク相関）ベースの IC（Information Coefficient）計算。
    - rank: 同順位は平均ランクを返すランク関数（浮動小数丸め対策あり）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算する統計サマリー。
  - zscore_normalize は kabusys.data.stats から再エクスポート。

- データプラットフォーム (kabusys.data)
  - calendar_management:
    - market_calendar を用いた営業日判定 API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 非存在時は曜日 (土日) ベースでフォールバックする設計。
    - calendar_update_job: J-Quants API から差分取得・バックフィル・健全性チェック付きで market_calendar を更新（fetch & save）。
  - ETL パイプライン:
    - pipeline.ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー一覧などを保持）。
    - pipeline モジュールに差分取得・保存・品質チェックの方針を記述（実装の骨格）。
  - data.etl に ETLResult を再エクスポート。

- モジュール公開整備:
  - ai/__init__.py, research/__init__.py, data/__init__ 等で主要関数を再エクスポートしパブリック API を整理。

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Known issues
- pipeline._get_max_date の末尾が不完全（ソースの一部が途中で切れているように見える: "return date.fro"）。ビルドや実行時に該当関数でエラーが発生する可能性があるため、リリース後に修正が必要。
- DuckDB バインドの互換性注意:
  - executemany に空リストを渡せない古い DuckDB バージョン（0.10 系）を考慮したガード実装があるが、利用する DuckDB バージョンにより挙動が変わる可能性がある。
- OpenAI API 依存:
  - news_nlp / regime_detector は OpenAI API キーが未設定だと ValueError を送出する。CI やテスト環境ではモック化（_call_openai_api の patch）を推奨。
- 時刻・タイムゾーン:
  - ニュース処理は JST ベースのウィンドウを UTC naive datetime に変換して扱っている。DB の datetime が UTC で保存されている前提のため、外部データのタイムゾーン扱いに注意が必要。

---

過去のリリース（より以前）が存在する場合はここに追記してください。今後のリリースでは Known issues の項目を解消した変更や API の互換性に関する注意を明示します。