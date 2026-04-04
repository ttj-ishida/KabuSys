# CHANGELOG

すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
リリース日はコードベースの現在日付（2026-04-04）を使用しています。

なお、本リリースはソースコードから推測して作成した初期リリース向けの変更履歴です。実際のリリースノート作成時はテスト結果や追加ドキュメント等に応じて調整してください。

## [0.1.0] - 2026-04-04

### Added
- パッケージ基盤
  - kabusys パッケージ初期実装。バージョン情報を src/kabusys/__init__.py にて `0.1.0` として定義。
  - public API 想定モジュール群を __all__ に定義: data, strategy, execution, monitoring（各モジュールの骨組みを想定）。

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定読み込みを行う自動ローダーを実装。
    - プロジェクトルート検出：.git または pyproject.toml を起点に検索（CWD に依存しない）。
    - 読み込み順序：OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き不可）。
    - 自動ロードの無効化：環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサの強化:
    - `export KEY=val` 形式対応。
    - シングル／ダブルクォート対応（バックスラッシュエスケープ考慮）。
    - インラインコメント判定の改善（クォート有無での振る舞い差別化）。
  - Settings クラスを実装し、アプリケーション設定をプロパティで提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_* トークン、DB パス、監視用設定、閾値、環境/ログレベルの検証など）。
    - 環境変数の必須チェック（_require）で未設定時に ValueError を発生させる。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値を限定）。
    - パス型設定は pathlib.Path で正規化・expanduser を適用。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析 (news_nlp)
    - raw_news / news_symbols テーブルを利用して銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信してセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - 時間ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を対象（UTC に変換して DB と比較）。
    - バッチ上限やトークン肥大対策: 最大 20 銘柄/バッチ、1銘柄あたり最大記事数・文字数制限を実装。
    - 再試行ロジック: 429, ネットワーク断, タイムアウト, 5xx に対する指数バックオフとリトライを実装。
    - レスポンスの厳格バリデーション: JSON 抽出、"results" リスト検証、コード整合性、数値検証、±1.0 でクリップ。
    - DB 書き込みは冪等性を考慮（対象コードのみ DELETE → INSERT）し、部分失敗時に既存スコアを保護。
    - API キーは引数経由または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。

  - 市場レジーム判定 (regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し、market_regime テーブルへ冪等書き込みを行う。
    - ニュース抽出はマクロキーワードリストに基づくフィルタを使用。
    - OpenAI 呼び出しは JSON mode を利用（gpt-4o-mini）し、複数回のリトライ戦略を実装。API 失敗時は macro_sentiment=0.0 とするフェイルセーフを採用。
    - lookahead バイアス防止設計：内部で datetime.today()/date.today() を参照せず、prices_daily も target_date 未満のデータのみを使用。
    - API キーは引数または環境変数 OPENAI_API_KEY。未設定時は ValueError。

- データモジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー管理ロジック（market_calendar テーブル参照）とユーティリティ実装:
      - 営業日判定: is_trading_day / is_sq_day
      - 隣接営業日探索: next_trading_day / prev_trading_day（最大探索日数制限を設定し無限ループを防止）
      - 期間内の営業日列挙: get_trading_days（DB 登録値優先、未登録日は曜日フォールバックで補完）
    - 夜間バッチ: calendar_update_job により J-Quants API から差分取得し保存（バックフィル・健全性チェック含む）。J-Quants クライアント経由で fetch/save を想定。
    - DB データがない場合は曜日ベースのフォールバック（週末除外）を採用。

  - ETL / pipeline
    - ETLResult データクラスを実装（target_date, fetched/saved counts, quality_issues, errors, ヘルパープロパティ）。
    - pipeline のインターフェース（ETLResult）の公開再エクスポートを実装。
    - ETL 設計方針として差分取得・バックフィル・品質チェック・idempotent な DB 保存を想定。

- 研究（research）モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M）、200日移動平均乖離、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB 上で計算する関数群を実装。
    - データ不足時の None ハンドリング、ログ出力、戻り値は (date, code) を含む dict のリスト。
    - DuckDB のウィンドウ関数を活用した効率的な SQL 実装。
  - feature_exploration
    - 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、rank、factor_summary（count/mean/std/min/max/median）などを実装。
    - horizons の入力検証、パフォーマンスを考慮したスキャン範囲拡張、外部依存を持たない純 Python 実装。

### Changed
- （初期リリースにつき既存機能の変更は無し）  

### Fixed
- （初期リリースにつき修正履歴は無し）

### Notes / Implementation details
- OpenAI 呼び出しは gpt-4o-mini と JSON Mode を想定。API 呼び出し関連のエラーはリトライやフォールバック（0.0）で安全側に動作するよう設計されていますが、正確な挙動は OpenAI API の挙動に依存します。
- AI 機能を利用するためには OPENAI_API_KEY が必要です（引数からの注入も可）。未設定だと例外を送出します。
- DuckDB をデータストアとして想定しており、SQL クエリは DuckDB 機能（ウィンドウ関数など）を利用して実装されています。
- DB 書き込みは可能な限り冪等に設計（DELETE → INSERT、BEGIN/COMMIT/ROLLBACK の使用）されています。
- 設定読み込みの自動化はパッケージ展開後も安全に動作するようにプロジェクトルート検出を行い、テスト時は自動ロードを無効化可能です。

### Known limitations / TODO
- 一部の戦略・実行・監視モジュール（strategy, execution, monitoring）は __all__ に列挙されているが、本リリースでの具体的な実装はコードベースからは限定的にしか確認できません。これらは将来のリリースで補完される想定です。
- news_nlp/regime_detector の OpenAI 呼び出し部分はテストのために差し替え可能な設計（モジュール内部関数の patch を想定）ですが、追加の統合テストやAPI利用制限対策（コスト管理等）が必要となります。
- ETL の品質チェックモジュール（quality）および J-Quants クライアント実装の詳細は外部モジュールに依存しているため、実環境での連携確認が必要です。

---

（以降のリリースはここに追記してください）