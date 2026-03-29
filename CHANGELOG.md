# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルはコードベースの内容から推測して作成されています。実際のコミット履歴がある場合は適宜差し替えてください。

## [0.1.0] - 2026-03-29
初回公開リリース（推測）。主要な機能群と設計方針を実装。

### Added
- パッケージ初期化
  - kabusys パッケージのエントリポイントを追加。__version__ = "0.1.0" を定義し、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルートを .git または pyproject.toml を基準に自動検出して .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化に対応）。
  - .env パーサーは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いなどに対応。
  - OS 環境変数を保護する protected パラメータ（.env.local の override 動作を制御）を導入。
  - 各種必須環境変数取得メソッドを提供（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN 等）。
  - env（development / paper_trading / live）・log_level のバリデーションとユーティリティ（is_live / is_paper / is_dev）を追加。
  - デフォルトの DB パス（DuckDB / SQLite）を設定可能。

- AI モジュール（kabusys.ai）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を用いて銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを算出して ai_scores テーブルへ書き込み。
    - 時間ウィンドウ（前日15:00 JST ～ 当日08:30 JST）に基づく処理。
    - バッチ処理（最大 20 銘柄 / チャンク）、1銘柄あたりのトークン肥大対策（最大記事数・最大文字数トリム）を実装。
    - OpenAI エラー（429・ネットワーク・タイムアウト・5xx）に対する指数バックオフリトライ、レスポンスの厳密な JSON バリデーションとフォールバック（外側の {} を抽出して復元）。
    - スコアは ±1.0 にクリップ。API 呼び出しはテスト時に差し替え可能（ユニットテスト向けに _call_openai_api を想定）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - マクロキーワードによる raw_news フィルタリング、OpenAI 呼び出し（gpt-4o-mini）、最大記事数制限、API リトライ、フェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
    - レジーム判定結果を market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar を用いた営業日判定（is_trading_day）、SQ 判定（is_sq_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日取得（get_trading_days）を実装。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動を採用。
    - night batch 用の calendar_update_job を実装し、J‑Quants クライアントから差分取得→保存（バックフィル・健全性チェックを含む）。
  - ETL パイプライン（kabusys.data.pipeline / kabusys.data.etl）
    - ETLResult データクラスを導入して ETL 実行結果（取得数・保存数・品質問題・エラー）を集約。
    - 差分更新、バックフィル、品質チェック（kabusys.data.quality との連携）を想定した設計。J-Quants クライアント経由での保存（idempotent）を前提。
    - DuckDB を利用した最大日付取得やテーブル存在チェック等のユーティリティを実装。
  - jquants_client（参照）：calendar と ETL の連携先として外部クライアントを想定（実装は別モジュール）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR）、Liquidity（20日平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB を用いて計算する関数を実装。
    - データ不足時の None 戻し、結果は (date, code) をキーとする辞書リスト形式。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン（calc_forward_returns）、IC（Spearman rank、calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず純粋 Python + DuckDB での実装。

### Changed
- 設計方針の明示化（コード内ドキュメント）
  - すべての分析・スコアリング処理でルックアヘッドバイアスを避けるため、datetime.today() / date.today() へ依存しない設計。
  - DuckDB 上での SQL ウィンドウ処理や ROW_NUMBER / LEAD / LAG を活用して効率的な集計を行う設計を採用。
  - OpenAI 呼び出しとニュース処理でモジュール間の結合度を下げるため、内部の API 呼び出し関数は各モジュールで独自に実装し、テスト時にパッチ可能にした。

### Fixed / Robustness
- .env パーサーの堅牢化
  - export プレフィックス対応、シングル／ダブルクォート内のバックスラッシュエスケープ処理、行中コメントの正しい扱いを実装して .env の多様な書式に対応。
  - key が空の行や不正行をスキップする安全処理を追加。
- 環境変数安全化
  - .env の読み込み時に OS 環境変数を保護する仕組み（protected set）を導入し、意図せぬ上書きを防止。
- OpenAI / ネットワーク障害耐性
  - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフのリトライ実装（news_nlp と regime_detector の双方）。
  - API レスポンスの JSON パース失敗や形式不正は警告ログを出してフェイルセーフ（デフォルトスコア 0.0 またはスキップ）で継続する挙動。
- DB トランザクション安全化
  - 書き込み処理で BEGIN / DELETE / INSERT / COMMIT を使用し、例外時に ROLLBACK を試行。ROLLBACK が失敗した場合でも警告ログを出力して上位に例外を伝播する設計。
- DuckDB 互換性対策
  - executemany に空リストを渡すと失敗する制約（DuckDB 0.10）へのワークアラウンドを導入（空チェックを行う）。

### Security
- API キー取り扱いの明示
  - OpenAI API キーは関数引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を発生させ使用者に通知。

### Notes / Known limitations
- 外部依存
  - OpenAI SDK（OpenAI）を利用する前提で実装されているため、実行環境に SDK と有効な API キーが必要。
  - J-Quants クライアント（kabusys.data.jquants_client）を通じた API 呼び出し実装は別途必要。
- 時刻取り扱い
  - 内部で使用する datetime は timezone-naive（UTC 換算済みの日付／時刻を前提）で統一されているため、外部連携時のタイムゾーン取り扱いに注意が必要。
- 一部機能は設計文書参照を前提（DataPlatform.md / StrategyModel.md 等の仕様に基づく実装）。

---

今後の項目（例）
- Unreleased:
  - strategy / execution / monitoring の具体実装（現状は __all__ に含めるのみ）。
  - 単体テスト・統合テストの追加（特に OpenAI 呼び出し周りのモック検証）。
  - パフォーマンス改善（大規模データ処理時のクエリ最適化）やログ／メトリクスの強化。

（この CHANGELOG はコード内容から推測して作成しています。実際の変更履歴とは差異がある可能性があります。）