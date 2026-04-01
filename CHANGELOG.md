# CHANGELOG

すべての重要な変更点を記載します。本ドキュメントは Keep a Changelog の書式に準拠しています。バージョン番号はパッケージ定義（kabusys.__version__）に合わせています。

※ 日付はリリース日を示します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-01
初回リリース

### Added
- パッケージ基盤
  - 初期パッケージ公開。パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - パブリック API として data, strategy, execution, monitoring をエクスポート候補として定義。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env および .env.local の自動ロード機能を追加（プロジェクトルート検出は .git / pyproject.toml を基準）。
  - 高度な .env パーサを実装: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなど。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB / 監視パラメータ等の設定値をプロパティで取得（必須項目は未設定時に ValueError）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）とユーティリティプロパティ（is_live, is_paper, is_dev）。

- AI: ニュースセンチメントと市場レジーム（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を基に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（ai_score）を算出して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ計算、バッチ（最大 20 銘柄）処理、1 銘柄あたりの記事数/文字数トリム、リトライ（429/ネットワーク/5xx）対策、レスポンス検証（JSON 抽出、結果バリデーション）、スコアクリップ（±1.0）などを実装。
    - テスト容易性を考慮し、内部の OpenAI 呼び出し関数を patch 可能に設計。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ冪等的に書き込む。
    - マクロキーワードによる raw_news フィルタ、OpenAI 呼び出しのリトライ / バックオフ、API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ実装。
    - ルックアヘッドバイアス防止のため、内部で日付の扱いを厳格化（target_date 未満のデータのみを使用）している。

- データプラットフォーム（src/kabusys/data）
  - calendar_management モジュール
    - JPX カレンダー（market_calendar）の夜間バッチ更新 job（calendar_update_job）を実装。J-Quants から差分取得して保存（冪等処理）するロジックを提供。
    - 営業日判定ユーティリティ：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。DB データ優先、未登録日は曜日ベースでフォールバック。探索上限を設けて無限ループを防止。
  - pipeline / etl モジュール
    - ETLResult データクラスの公開（kabusys.data.pipeline.ETLResult を kabusys.data.etl で再エクスポート）。
    - ETL の設計方針（差分更新、バックフィル、品質チェック）とユーティリティ関数群を実装（部分的に pipeline モジュール内で定義）。
  - jquants_client を介したデータ取得・保存を想定した設計（fetch/save の抽象化を想定）。

- Research（src/kabusys/research）
  - factor_research モジュール
    - Momentum, Value, Volatility, Liquidity などのファクター計算関数を実装（calc_momentum, calc_value, calc_volatility）。DuckDB の SQL ウィンドウ関数を利用して効率的に計算。
    - 欠損やデータ不足時の扱いを定義（例: ma200_dev はデータ不足時 None）。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない純粋 Python 実装を目指し、統計処理の基本機能を提供。
  - research パッケージの __all__ で主な関数を公開。

### Changed
- 設計上の重要方針を明文化
  - すべての分析・AI モジュールでルックアヘッドバイアスを避ける設計（datetime.today()/date.today() の直接参照禁止や、SQL で date < target_date の排他条件）を採用。
  - DB 書き込みは可能な限り冪等に（DELETE → INSERT / ON CONFLICT 戻り）して部分失敗時のデータ保護を考慮。
  - OpenAI 呼び出しの失敗はフェイルセーフ的にスキップまたは 0.0 フォールバックし、上位処理を破壊しない方針を採用。

### Fixed
- OpenAI レスポンスの堅牢性向上
  - JSON Mode のレスポンスに余計な前後テキストが付くケースを想定し、最外の {} を抽出してパースする保護処理を追加。
  - API エラーの分類（RateLimitError / APIConnectionError / APITimeoutError / APIError）に対するリトライ・非リトライ判定を実装。
- .env ファイル読み込みの堅牢化
  - ファイル読み込み失敗時の警告、読み込み条件（override/protected）を導入し、OS 環境変数を保護。

### Security
- 環境変数管理で OS の既存環境を上書きしない安全な既定挙動（.env は override=False、.env.local は override=True でただし protected を考慮）を採用。
- API キーや機密情報は Settings の必須プロパティとして明示し、未設定時に明確なエラーメッセージを返すことで誤ったデプロイを検出しやすくしている。

### Known limitations / Notes
- 初期実装のため以下の点に留意してください。
  - OpenAI API（gpt-4o-mini）利用箇所は実行時に API キー（OPENAI_API_KEY）が必要。テスト時は内部 _call_openai_api を patch してモック可能。
  - DuckDB のバージョン差異に起因するバインドや executemany の制約（空リスト不可など）を考慮した実装を行っているが、実環境での動作確認を推奨。
  - データベーステーブルスキーマ（prices_daily, raw_news, ai_scores, market_calendar, raw_financials 等）に依存するため、初回導入時はスキーマ準備が必要。
  - strategy / execution / monitoring パッケージのエクスポートは定義済みだが、本リリースに戦略の発注実装や監視デーモン本体が含まれていない可能性がある（今後の実装予定）。

### Breaking Changes
- なし（初回リリース）

---

今後のリリースでは、strategy（売買ロジック）・execution（発注実装）・monitoring（運用監視）の実装拡充、テストカバレッジ追加、ドキュメント整備、バイナリ互換性の保持などを予定しています。必要であれば、この CHANGELOG を英語版に翻訳したり、より細かなコミット単位の変更履歴を生成したりできます。