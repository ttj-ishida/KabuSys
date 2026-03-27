# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
このファイルは、リポジトリ内のソースコード（src/kabusys 以下）から仕様・実装内容を推測して作成した初期の変更履歴です。

注: バージョンはパッケージルートの __version__（0.1.0）に基づきます。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買・データ基盤・リサーチ・AI分析を目的としたコアモジュール群を実装。

### 追加 (Added)

- パッケージ基礎
  - kabusys パッケージ初期公開。公開 API は data, research, ai, config, research サブパッケージ等。
  - __version__ を "0.1.0" として設定。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサ実装: export 付き行、クォート内のエスケープ、インラインコメントの扱い、無効行スキップ等に対応。
  - override / protected 機能により OS 環境変数を保護して .env を上書きしない動作をサポート。
  - 必須環境変数取得用 Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - DB のデフォルトパス: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db。
  - KABUSYS_ENV / LOG_LEVEL の検証ロジックを追加（許容値チェック）。

- AI / 自然言語処理 (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込む機能（score_news）。
    - リクエストのバッチ化（最大 20 銘柄/チャンク）、トークン肥大化対策（記事数・文字数でトリム）。
    - JSON Mode を用いた厳密な JSON レスポンス期待。レスポンスの堅牢なパースとバリデーション実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ処理。
    - API 失敗時は部分スキップを行い、可能な限り他銘柄の結果を保存（部分失敗耐性）。DuckDB の executemany 空リスト制約を考慮した実装。
    - テスト容易性を考慮し、内部の OpenAI 呼び出し関数をモック差し替え可能に設計。

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ冪等書き込み（score_regime）。
    - ニュースの抽出は kabusys.ai.news_nlp の calc_news_window を利用。LLM 呼び出しは独立実装でモジュール結合を抑制。
    - OpenAI 呼び出し失敗時は macro_sentiment=0.0 としてフォールバック（フェイルセーフ）。
    - LLM 呼び出しに対するリトライと 5xx の扱い、JSON パース保護を実装。
    - ルックアヘッドバイアス防止のため、内部で datetime.today() / date.today() を参照しない設計（target_date を明示的に与える）。

- データプラットフォーム (src/kabusys/data)
  - ETL / パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - 差分更新、バックフィル、品質チェックを統合する ETLResult データクラスとパイプラインのインターフェース実装。
    - ETLResult により取得件数・保存件数・品質問題・エラー集約が可能。
    - DuckDB のテーブル存在チェック・最大日付取得などのユーティリティを実装。

  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar を扱うユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - J-Quants から差分取得し market_calendar を冪等更新する夜間バッチ（calendar_update_job）。
    - カレンダーデータ未取得時は曜日ベースでフォールバック。DB 値が優先される一貫した判定ロジック。
    - 最大探索日数や健全性チェック、バックフィル設計を導入して異常値・無限ループを防止。

- リサーチ（ファクター計算 / 特徴量探索） (src/kabusys/research)
  - ファクター計算モジュール (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。
    - DuckDB を用いた SQL ベースの実装。データ不足時の None ハンドリング。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 将来リターン（指定ホライズン）を一括取得する汎用実装。
    - calc_ic: スピアマン順位相関（IC）を計算し、データ不足時は None を返す。
    - rank: 同順位は平均ランクを割り当てる実装（丸めで ties を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
  - research パッケージは zscore_normalize（kabusys.data.stats から再公開）や上記関数群をエクスポート。

- その他
  - テストしやすさを考慮して、内部の API 呼び出し部分（OpenAI クライアント呼び出し等）がモック差し替え可能な構成。

### 変更 (Changed)

- なし（初回リリース）

### 修正 (Fixed)

- エラー耐性とフォールバックを強化
  - AI モジュール: OpenAI API の 5xx/タイムアウト/レート制限に対する再試行戦略と、全リトライ失敗時の安全なフォールバック（0.0）を導入。
  - news_nlp: レスポンス JSON の前後に余分なテキストが混入するケースを考慮したパースロジックを追加。
  - ETL / DB 操作: DuckDB の executemany に対する空パラメータ制約を考慮した保護ロジックを実装（部分書き込みで既存データを保護）。

### 既知の制限・注意点 (Known issues / Notes)

- OpenAI モデルは gpt-4o-mini を想定しているが、将来的なモデル差替えや OpenAI SDK の仕様変更に対しては互換性の検証が必要。
- LLM レスポンスは「厳密な JSON」を期待する実装だが、現実的には前後テキストや型の違いが発生しうるためパースは寛容に実装している（ただし誤った形式はスキップされる）。
- .env 自動読み込みは便利だが、既存の OS 環境変数を上書きしない設計（protected）でも、意図しない読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- score_news / score_regime は target_date を明示的に渡す設計（内部で today を参照しない）。運用時は正しい基準日を渡すこと。
- ai_scores 書き換えは「部分置換」方式を採用しており、部分失敗時でも既存スコアを保護するが、完全なトランザクション整合性（複数テーブル横断）は保証していない。
- DuckDB への依存を前提としているため、別 RDB を利用する場合は移植コストが発生する。

### セキュリティ (Security)

- 環境変数に API キー等の機密情報を要求する（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）。これらは .env または OS 環境変数で供給すること。
- 自動 .env ロード機能は環境により機密情報を誤読する可能性があるため、CI / 本番環境では KABUSYS_DISABLE_AUTO_ENV_LOAD の使用を検討してください。

---

今後の予定（提案）
- CI テストケースとユニットテストの追加（DuckDB のインメモリを用いたテストを想定）。
- monitoring / execution / strategy の実装と統合テスト。
- API 呼び出し・レスポンスの監視・メトリクス収集機能の追加。