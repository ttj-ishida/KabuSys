# Changelog

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠し、意味のある変更のみを記載します。

最新リリース: 0.1.0 (2026-03-29)

## [0.1.0] - 2026-03-29

初回リリース。KabuSys のコア機能を実装しました。主な追加点と設計上の重要事項を以下にまとめます。

### 追加 (Added)
- パッケージ基盤
  - src/kabusys/__init__.py によりパッケージを公開。バージョンは 0.1.0、公開モジュールは data, strategy, execution, monitoring（将来の拡張を想定）。
- 設定/環境変数管理
  - src/kabusys/config.py を追加。
    - .env / .env.local ファイルの自動読み込み機構（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - エクスポート形式（export KEY=val）やクォート/エスケープ、行末コメントの取り扱いに対応する堅牢な .env パーサー。
    - 必須環境変数チェック `_require` と Settings クラス（J-Quants, kabuAPI, Slack, DB パス, 実行環境・ログレベル判定などのプロパティ）。
    - 環境値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。
- AI（NLP）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores に書き込む機能を実装。
    - 時間ウィンドウ（JST基準：前日15:00〜当日08:30）計算ユーティリティ calc_news_window を提供。
    - バッチ処理（銘柄ごとに最大 _BATCH_SIZE=20）・記事数/文字数のトリミング、API リトライ（429/ネットワーク/5xx のエクスポネンシャルバックオフ）を実装。
    - レスポンスの厳密なバリデーションと JSON Mode（余計な前後テキストの補正処理含む）。スコアは ±1.0 にクリップ。
    - 部分失敗を考慮した冪等書き込み（DELETE → INSERT、失敗時に他銘柄の既存データを保護）。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存する機能を実装。
    - MA 計算はルックアヘッドを防ぐため target_date 未満のデータのみを使用。ニュースは news_nlp.calc_news_window を利用。
    - OpenAI 呼び出しは独立実装、リトライ/フェイルセーフ（API 失敗時 macro_sentiment=0.0）を採用。
    - レジーム合成ロジック、閾値、および冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。
- データ基盤（Data）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar）管理と営業日ロジックを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。DB データがない場合は曜日（平日）ベースのフォールバックを行う。
    - calendar_update_job により J-Quants から差分取得して冪等に保存する処理を実装（バックフィル、健全性チェック含む）。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）など安全策を実装。
  - src/kabusys/data/pipeline.py
    - ETL パイプライン結果を表す ETLResult データクラスを実装。
    - 差分取得・バックフィル・品質チェックのためのユーティリティを整備（内部ユーティリティ: _get_max_date 等）。
    - DataPlatform の設計方針に基づく idempotent 保存、品質問題の集約（呼び出し元での判断を想定）。
  - src/kabusys/data/etl.py
    - pipeline.ETLResult の再エクスポート。
  - src/kabusys/data/__init__.py（パッケージ用）
  - jquants_client と quality モジュール（呼び出し）を想定した設計（実際のクライアント実装は別途）。
- Research モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER, ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 上で SQL を駆使して計算。データ不足時の None ハンドリングを厳密に行う。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient：calc_ic）、ランク付けユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等外部依存を排し、標準ライブラリ + DuckDB で実装。
  - src/kabusys/research/__init__.py にて主要関数を公開。
- テスト/実装補助
  - OpenAI 呼び出し部分はユニットテストで差し替え可能な設計（各モジュールで private 関数を個別実装）。

### 変更 (Changed)
- 初版のため「変更」は特になし（初回リリース）。

### 修正 (Fixed)
- 初版のため「修正」は特になし。

### セキュリティ (Security)
- OpenAI API キーの取り扱いは引数注入または環境変数（OPENAI_API_KEY）を想定。API キー未設定時は ValueError を発生させることで誤動作を防止。
- .env 自動ロードで OS 環境変数を保護するため protected set を用いて上書きを制御。

### 設計上の注意（重要な振る舞い）
- ルックアヘッドバイアス防止：多くの処理で datetime.today()/date.today() を直接参照せず、関数引数の target_date に依存する設計。
- フェイルセーフ戦略：外部 API の失敗やパースエラーは基本的に例外で止めずフォールバック値（例：macro_sentiment=0.0）を使って継続する方針。
- DB 書き込みは冪等化を重視（DELETE→INSERT、ON CONFLICT を想定した保存など）。
- DuckDB 0.10 の制約（executemany に空リストを投げられない等）に配慮した実装が散見される。
- OpenAI の JSON Mode を利用しつつも、稀に余計なテキストが混ざるケースを復元するロジックを実装。

---

今後の予定（未実装・想定）
- strategy / execution / monitoring パッケージの実体実装（現在は __all__ にプレースホルダ存在）。
- jquants_client / quality モジュールの具体実装連携。
- エンドツーエンドの統合テスト、CI 設定、ドキュメントの充実化。

もし CHANGELOG に追加してほしい詳細（例：特定ファイルの実装方針やトレーサビリティ情報、変更履歴の分割など）があれば教えてください。