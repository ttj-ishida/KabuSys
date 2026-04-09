# Changelog

すべての変更は「Keep a Changelog」方式に従い、セマンティックバージョニングで管理します。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

## [0.1.0] - 2026-04-09

### 追加
- パッケージ初期公開: kabusys（日本株自動売買システム）を公開。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - エクスポート: data, strategy, execution, monitoring を公開。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイル自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env ファイルパーサを実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - 環境変数を保護するための `protected` 機構を導入（OS 環境変数を上書きしない）。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視 / システム設定をプロパティ経由で取得可能に。
  - 設定値のバリデーションを導入（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。不正値時は ValueError を送出。
  - ファイルパス系設定は Path オブジェクトで正規化（expanduser）。

- AI（自然言語処理）モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとのニュースを OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - JSON Mode のレスポンスを厳密に検証してスコアを抽出する `_validate_and_extract` を実装。前後余計なテキストが混ざるケースの復元処理あり。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対するエクスポネンシャルバックオフでのリトライ実装。
    - API 呼び出し部分を `_call_openai_api` に分離し、ユニットテストでモック可能に。
    - DuckDB への書き込みは部分成功耐性を考慮（スコア取得済みコードのみ DELETE → INSERT）し、DuckDB の executemany 空リスト制約に対応。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースタイトル抽出、OpenAI 呼び出し（gpt-4o-mini）で JSON レスポンスをパースしてスコア化。
    - API エラー時はフェイルセーフとして macro_sentiment=0.0 を採用。
    - マーケットレジーム結果を冪等に DuckDB の market_regime テーブルへ書き込み（BEGIN/DELETE/INSERT/COMMIT、例外時は ROLLBACK）。
    - 設計上ルックアヘッドバイアスを避ける（date < target_date 等、datetime.today() を参照しない）。

- データ処理・ETL（src/kabusys/data）
  - ETL パイプラインインターフェース（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを導入し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を構造化して返却・ログ出力可能に。
    - 差分更新、バックフィル、品質チェックの設計方針をコード内に反映。

  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを使った営業日判定・探索ユーティリティを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 未登録日の曜日ベースフォールバック（週末は非営業日）を採用し、DB 登録がある場合は DB 値を優先。
    - calendar_update_job を実装し J-Quants API から差分取得 → 保存（バックフィル・健全性チェック含む）。
    - jquants_client を利用して取得/保存を委譲。

- リサーチ機能（src/kabusys/research）
  - factor_research モジュールを実装（calc_momentum, calc_value, calc_volatility）
    - モメンタム（1M/3M/6M リターン）、MA200 乖離、ATR20、出来高/売買代金の移動平均等を DuckDB の SQL と Python で計算。
    - 欠損・データ不足時の None 処理（例: MA200 に足りない場合は None）。
  - feature_exploration モジュールを実装（calc_forward_returns, calc_ic, factor_summary, rank）
    - 将来リターン計算（複数ホライズン）、Spearman ランク相関（IC）、要約統計量、ランク変換（同順位は平均ランク）を提供。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

### 変更（設計上の注意・改善）
- テスト性を考慮して OpenAI 呼び出しをファクトリ化 / プライベート関数化し、unittest.mock.patch で差し替え可能に（news_nlp._call_openai_api, regime_detector._call_openai_api）。
- すべての「日付」を明示的に date / datetime オブジェクトで扱い、timezone 混入を防止。ルックアヘッドバイアス対策のため datetime.today()/date.today() を主要ロジックで参照しない設計。
- DuckDB 特有の注意（executemany に空リストを渡せない等）へ対処するため、書き込み前に空チェックを追加。
- OpenAI レスポンスの堅牢なパース（JSON 以外の前後余計文字の復元）と、レスポンス検証ルール（期待するキー・型・有限値）を明示。

### 修正（フェイルセーフ・互換性）
- OpenAI API のエラー種別に応じたリトライ戦略（RateLimitError, APIConnectionError, APITimeoutError, APIError の 5xx 判断）を実装し、非致命的失敗はスキップして継続するフェイルセーフを採用。
- API キー未設定時の明示的なエラーメッセージ（ValueError）を追加（news_nlp.score_news, regime_detector.score_regime）。
- market_calendar の NULL 値検出時に警告ログを出力し、フォールバックへ切替える安全動作を実装。

### ドキュメント（コード内ドキュメント）
- 各モジュール（AI, data, research 等）に設計方針、処理フロー、パラメータ説明、返値仕様を詳細にドキュメント化（docstring 内に記載）。
- 単体テスト用の注記（どの関数をモックすべきか）を明記。

### 既知の制約 / 注意事項
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON Mode を使用する設計だが、API バージョン/挙動の変化により追加対応が必要になる可能性がある。
- DuckDB 依存（SQL 実行結果の型等）により一部環境差異が発生する可能性があるため、運用環境での DB バージョン確認を推奨。
- 現バージョンでは一部ファクター（PBR・配当利回り）は未実装。
- strategy / execution / monitoring の具体的実装はエクスポートされているが、本リリースでの詳細実装はコードベース内に委譲される（本 CHANGELOG は提供されたコード範囲に基づく）。

---

今後のリリースでは、明示的な API 互換性改善、追加ファクター、LINE 通知・発注ロジック、テストカバレッジ向上、運用監視の拡充等を想定しています。必要であれば各モジュール別の詳細な変更履歴（関数単位の変更点）も生成します。