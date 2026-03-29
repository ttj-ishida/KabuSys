# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
※初期リリースの内容はソースコードから推測して記載しています。

全般的な方針:
- 日付はリリース日を示します。
- 実装の設計上、ルックアヘッドバイアスを防ぐために datetime.today()/date.today() を直接参照しないようにしています（テスト・運用上の注意点として明記）。

## [Unreleased]

## [0.1.0] - 2026-03-29

### Added
- 全体
  - パッケージ初期版を追加。パッケージ名: `kabusys`。トップレベルで公開するサブパッケージ: `data`, `strategy`, `execution`, `monitoring` を __all__ に定義。
  - バージョンを `0.1.0` として固定 (`src/kabusys/__init__.py`)。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイル（`.env`, `.env.local`）または既存の OS 環境変数から設定を読み込む自動ロード機能を実装。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - プロジェクトルート検出を .git または pyproject.toml を基準に実装（パッケージ配布後も CWD に依存せず動作）。
  - .env パーサーを実装:
    - `export KEY=val` 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - インラインコメントの判定（クォート外で直前がスペース/タブの `#` をコメント扱い）対応。
  - .env ロード時のオーバーライド挙動:
    - `.env` は OS 環境変数で未設定のキーのみ設定。
    - `.env.local` は上書き（ただし起動時の OS 環境変数は保護）。
  - `Settings` クラスを提供（`settings = Settings()`）:
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを定義。
    - 環境変数の必須チェック (`_require`) と値検証（`KABUSYS_ENV` や `LOG_LEVEL` の許容値チェック）を実装。
    - プロパティ: `is_live`, `is_paper`, `is_dev` を提供。

- AI 関連（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を使って銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントスコアを算出。
    - 対象時間ウィンドウは JST ベースで前日 15:00 ～ 当日 08:30（UTC で前日 06:00 ～ 23:30）に変換して使用するユーティリティ `calc_news_window` を実装。
    - バッチサイズ、トークン肥大対策（1銘柄あたりの最大記事数／文字数）や 20 銘柄単位のチャンク処理を実装。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフを実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスのバリデーションを厳密に実施（JSON の復元処理、results リストの存在確認、code/score の型チェック、スコアの ±1.0 クリップ）。
    - DB への書き込みは、部分失敗時に既存スコアを保護するため「対象コードのみ DELETE → INSERT」の冪等更新を実施（DuckDB の executemany の空リスト制約に配慮）。
    - テスト容易性のため、内部の OpenAI 呼び出し関数 `_call_openai_api` を `unittest.mock.patch` で差し替え可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF (1321) の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（"bull" / "neutral" / "bear"）を判定する機能を実装。
    - MA の乖離計算は対象日未満のデータのみを使用し、データ不足時は中立（1.0）を返すなどルックアヘッドを防止。
    - マクロニュースは `news_nlp.calc_news_window` に基づく期間で raw_news からフィルタし、OpenAI で評価。記事が無い場合は LLM 呼出をせず中立（0.0）で継続。
    - OpenAI 呼び出しでの冗長系（429・ネットワーク等）に対するリトライとフォールバック（最終的に 0.0）を実装。
    - レジームスコアは合成後クリップし閾値でラベル化。結果は `market_regime` テーブルへ冪等で書き込む（BEGIN/DELETE/INSERT/COMMIT）。
    - モジュール分離のため、OpenAI 呼び出し実装は news_nlp と共有しない（結合を避ける設計）。
    - デフォルトモデル: `gpt-4o-mini`、再試行回数等は定数化。

- データプラットフォーム（src/kabusys/data）
  - calendar_management.py
    - JPX カレンダー（market_calendar）の取得・管理ロジックを実装。
    - 営業日判定ユーティリティ群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB 登録がない場合の曜日ベースのフォールバック、DB 登録がある場合は DB 値優先といった一貫した挙動を実装。
    - calendar_update_job を実装し、J-Quants クライアントから差分取得して market_calendar を冪等更新。バックフィル、健全性チェック（未来日付の異常検出）を実装。
  - pipeline.py / etl.py
    - ETL のハイレベル設計に基づく実装。差分取得、保存、品質チェックのフローを想定。
    - ETLResult データクラスを実装（target_date、取得/保存件数、品質問題、エラー等を保持）。`to_dict()` により品質問題をシリアライズ可能。
    - DuckDB を用いた最終日付検出やテーブル存在チェック等のユーティリティを実装。
    - デフォルトのバックフィル日数、カレンダー先読み日数、初回ロード用の最小日付等を定義。

- リサーチ（src/kabusys/research）
  - factor_research.py
    - ファクター計算（Momentum / Value / Volatility / Liquidity）の実装:
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離（200行未満は None）
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率
      - calc_value: EPS/ROE を raw_financials から取得して PER/ROE を計算（未実装項目は注記）
    - DuckDB のウィンドウ関数を活用して効率的に算出。外部 API へのアクセスは行わない（安全設計）。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）を実装。複数ホライズンをまとめて取得する SQL を採用し、ホライズンの整合性チェックを実装。
    - IC（Information Coefficient）計算機能（calc_ic）を実装: ランク相関（Spearman）を自前実装。
    - ランク変換ユーティリティ（rank）と統計サマリー（factor_summary）を提供。pandas 等に依存しない純 Python 実装。

- テスト・開発配慮
  - 内部で外部 API を呼ぶ箇所（OpenAI 呼び出し等）は差し替え可能に実装し、ユニットテスト容易性を確保。
  - 操作ミスを防ぐため、DB の executemany 空リスト問題（DuckDB 0.10）に配慮したガードを追加。

### Changed
- n/a（初回リリースのため変更履歴なし）

### Fixed
- n/a（初回リリースのため修正履歴なし）

### Security
- 環境変数読み込みで OS 側の環境変数を保護する仕組みを導入（自動 .env ロード時に起動時の os.environ キーを protected として扱う）。

### Notes / Known limitations
- OpenAI の利用:
  - OpenAI API キー（環境変数 `OPENAI_API_KEY` または各関数引数）が必須。未設定時は ValueError を送出する。
  - モデルは `gpt-4o-mini` を想定。料金・レイテンシに注意。
- DuckDB に依存:
  - 実行環境に DuckDB が必要。DuckDB バージョン差異（例えば executemany の空リスト挙動）に配慮した実装を行っているが、運用環境の DuckDB バージョン確認を推奨。
- ルックアヘッド回避:
  - 日付の取り扱いは厳格に行われている（target_date 未満/排他条件の厳守）。ETL/解析実行時は target_date の指定に注意。
- 未実装 / 将来対応候補:
  - factor_research の PBR、配当利回りなどは現バージョンでは未実装（注記あり）。
  - jquants_client の実装は参照されているが（calendar/pipeline 等）、ここに含まれるクライアント実装の詳細は別モジュール（src/kabusys/data/jquants_client）に依存する想定。

---

（補足）この CHANGELOG は現行ソースコードの実装とドキュメント文字列から推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース管理ポリシーに合わせて調整してください。