# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに従って管理されています。  

注: 日付はソースから推測した初回リリース日として 2026-03-31 を使用しています。

[Unreleased]
- なし

[0.1.0] - 2026-03-31
Added
- 全体
  - 初回公開版として kabusys パッケージを追加。
  - パッケージバージョンを __version__ = "0.1.0" に設定。
  - パッケージ公開 API に data, strategy, execution, monitoring を想定したエクスポートを追加（__all__）。

- 環境設定 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を起点に探索し、CWD に依存しない実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env の行パースは export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメント取り扱い等に対応。
    - .env.local は .env より優先して上書き（ただし既存の OS 環境変数は保護）。
  - Settings クラスを提供し、プロパティ経由で設定値を取得（必須値は未設定時に ValueError を送出）。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などを含む。
  - 環境値検証:
    - KABUSYS_ENV は development / paper_trading / live のみ許容。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容。
  - データベースパス設定（DUCKDB_PATH, SQLITE_PATH）の Path 解決をサポート。

- AI / NLP (kabusys.ai)
  - ニュースセンチメント (news_nlp)
    - raw_news と news_symbols を元に、銘柄ごとにニュースを集約し OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（最大 20 銘柄/回）、記事トリム（最大記事数・最大文字数）などのトークン肥大化対策を実装。
    - OpenAI 呼び出しは JSON mode を使用し、レスポンスの厳密バリデーションとパース復元（前後ノイズの {} 抽出）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライと、非再試行ケースの適切なスキップを実装。
    - スコアは ±1.0 にクリップ。失敗時は部分的に結果を書き換え（該当コードのみ DELETE → INSERT）して既存データ保護。
    - テスト容易性のため _call_openai_api を patch 可能に実装。
  - 市場レジーム判定 (regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する機能を実装。
    - マクロニュース抽出はマクロキーワード群でフィルタし、最大 20 記事を対象に LLM でセンチメントを算出。
    - OpenAI 呼び出しのリトライ・エラー処理・JSON パース失敗時のフェイルセーフ（macro_sentiment = 0.0）を実装。
    - レジーム合成スコアはクリップし閾値によりラベルを決定。結果は market_regime テーブルへ冪等に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易性のため _call_openai_api を別実装で保持（news_nlp と結合しない設計）。

- データ処理 / ETL (kabusys.data)
  - calendar_management
    - JPX カレンダー管理（market_calendar を利用）と営業日判定ユーティリティ群を実装。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - データが存在しない場合は曜日ベース（平日）でフォールバックする一貫した挙動。
    - 次/前営業日の探索は最大探索日数を設定して無限ループを防止。
    - 夜間バッチ更新 calendar_update_job を実装。J-Quants から差分取得し市場カレンダーを idempotent に保存（fetch + save を利用）。
    - バックフィル、健全性チェック（極端に未来日がある場合スキップ）を実装。
  - pipeline / ETLResult
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー一覧などを格納）。
    - _get_max_date 等の内部ユーティリティで差分更新ロジックに利用。
    - data.etl で ETLResult を再エクスポート。
  - jquants_client との連携を想定した差分取得・保存フローおよび品質チェックの設計を含む（quality モジュールとの連携を想定）。

- リサーチ / ファクター (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ATR 等の定量ファクター計算関数を実装:
      - calc_momentum, calc_volatility, calc_value を提供。すべて prices_daily / raw_financials を参照し、外部 API に依存しない。
    - 計算は DuckDB のウィンドウ関数と SQL を併用して効率的に実行。
  - feature_exploration
    - 将来リターン計算 calc_forward_returns（任意ホライズン、ホライズン検証あり）。
    - IC（Information Coefficient）計算 calc_ic（スピアマンのランク相関）、ランク変換ユーティリティ rank。
    - factor_summary により各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
  - research.__init__ で主要関数を再エクスポートし研究ワークフローから利用可能。

- 実装上の設計方針・品質面の追加
  - ルックアヘッドバイアスの排除: datetime.today() / date.today() をスコア算出関数内部で直接参照しない設計（target_date を明示的引数として受け取る）。
  - DB 書き込みは冪等性を重視（DELETE→INSERT や ON CONFLICT を想定）し、失敗時は ROLLBACK を試行して例外を伝播。
  - OpenAI 呼び出しは JSON モードを利用し、レスポンスの厳密な検証・クリッピング・部分失敗時の保護を実装。
  - テスト容易性: OpenAI 呼び出し箇所は patch で差し替え可能にしてユニットテストを容易化。
  - DuckDB 互換性考慮: executemany に空リストを渡してはならない等の既知制約を考慮した実装。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Known limitations
- OpenAI API キーが未設定の場合、score_news / score_regime は ValueError を送出する。CI/本番では OPENAI_API_KEY を設定する必要あり。
- news_nlp / regime_detector は gpt-4o-mini（JSON mode）を前提としているためモデルの互換性に注意。
- calendar_update_job などは jquants_client の実装に依存するため、実行前に外部クライアント実装・認証情報を用意する必要あり。
- 一部モジュール（strategy, execution, monitoring）の詳細実装はこのリリースでは提示されていないが、パッケージのエクスポート候補として名前空間には含まれている（将来追加予定）。

---

メンテナンスや次リリースで期待される作業（提案）
- strategy / execution / monitoring の具体的実装追加（取引ロジック・注文エンジン・監視アラート）。
- テストカバレッジ強化（DuckDB を用いた統合テスト、OpenAI 呼び出しのモック検証）。
- ドキュメント（使用例、設定例、運用手順）の整備。
- 互換性向上（OpenAI SDK のバージョン変化に対応するラッパー等）。