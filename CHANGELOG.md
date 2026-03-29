# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [Unreleased]
- 現時点で未リリースの変更はありません。

## [0.1.0] - 2026-03-29
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を追加。
  - パッケージ公開シンボル: data, strategy, execution, monitoring を __all__ で公開。

- 設定 / 環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml）。
  - 環境変数自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメント処理をサポート。
  - 環境変数読み込みの上書き/保護ロジック（override / protected）を実装。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等のアクセスを提供。
  - 環境値検証: KABUSYS_ENV と LOG_LEVEL の許容値チェック、未設定時の ValueError。

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）の JSON モードで銘柄別センチメントを算出し、ai_scores テーブルへ書き込む。
    - 日次ニュースウィンドウ（JST 前日15:00〜当日08:30）計算ユーティリティを提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数/文字数制限、レスポンス検証、スコアクリップ（±1.0）を実装。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフリトライとフェイルセーフ（失敗時は対象銘柄をスキップ）を実装。
    - DuckDB 互換性のため、executemany に空リストを渡さない安全な DB 書き込み処理。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini JSON モード）、API リトライ、JSON パース安全化、フェイルセーフの実装。
    - ルックアヘッドバイアス防止設計（date 比較は排他条件等で実装）。

- Data モジュール (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理ロジック（market_calendar の存在判定、営業日判定、次/前営業日探索、期間内営業日取得、SQ日判定）を実装。
    - DBに登録のない日付は曜日ベースのフォールバック（週末は非営業日）。
    - next_trading_day / prev_trading_day は最大探索日数制限で保護。
    - calendar_update_job により J-Quants から差分取得 → 冪等保存、バックフィル、健全性チェックを実装。
  - pipeline / ETL:
    - ETLResult データクラスを公開（ETL 実行結果の集約とシリアライズ機能）。
    - 差分更新・バックフィル・品質チェック方針を踏まえた ETL 基盤の骨組みを実装（jquants_client と quality モジュールとの連携想定）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- Research モジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER / ROE）計算を実装。prices_daily / raw_financials を参照。
    - データ不足時の None 処理やログ出力の明確化。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク変換（同順位は平均ランク）、ファクター統計サマリー（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - data.stats の zscore_normalize を再エクスポート（__init__ で公開）。

### Changed
- 初回リリースのため変更履歴はなし（基盤実装として多数の機能を追加）。

### Fixed
- 初回リリースのため修正履歴はなし（実装段階で設計上のフェイルセーフや互換性考慮を反映済み）。

### Security
- OpenAI API キーや外部トークン等は Settings 経由で環境変数から取得する設計。API キー未設定時は ValueError を発生させ、軽微な誤設定での暴走を防止。

### Notes / 設計上の重要ポイント（リリースノート補足）
- ルックアヘッドバイアス対策:
  - AI スコアリング・レジーム判定・ファクター計算は内部で date.today() や datetime.today() を参照せず、呼び出し元が指定した target_date の過去データのみを参照する設計。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）呼び出しが失敗してもプロセス全体が例外で停止しないよう、個別処理はスキップやデフォルト値（例: macro_sentiment=0.0）で継続する挙動を採用。
- DuckDB 互換性:
  - executemany に空リストを渡さない等、DuckDB のバージョン差異を考慮した実装が含まれる。
- テスト容易性:
  - OpenAI 呼び出し箇所は内部の _call_openai_api を patch して差し替え可能にしており、ユニットテストで外部依存をモックしやすい設計。

---

今後の予定（例）
- strategy / execution / monitoring の具体的な取引・監視ロジックの追加。
- テストカバレッジ拡充、CI パイプラインの整備。
- J-Quants / kabu API クライアントの実装強化と運用監視機能の追加。