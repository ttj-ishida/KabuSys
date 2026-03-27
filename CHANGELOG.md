# CHANGELOG

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお本履歴はソースコードの内容から機能追加・修正点を推測して記載しています。

## [0.1.0] - 2026-03-27

初回公開リリース。本リリースでは日本株自動売買システムのコア機能群（環境設定、データETL、マーケットカレンダー、AIベースのニュース解析・レジーム判定、リサーチ用ファクター計算など）を提供します。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージを導入。バージョン情報を __version__ = "0.1.0" として公開。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に含めてエクスポート。

- 環境設定
  - robust な .env 読み込み実装（src/kabusys/config.py）。
    - プロジェクトルート自動検出: .git または pyproject.toml を親ディレクトリから探索する _find_project_root を実装。
    - .env / .env.local の自動読み込み（OS 環境変数を保護しつつ .env.local で上書き可能）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを抑止可能。
    - export KEY=val 形式や、シングル/ダブルクォートおよびエスケープ対応のパーサー _parse_env_line を実装。
    - 上書き禁止キーセット（protected）により OS 環境を保護する読み込みロジックを実装。
  - Settings クラスで各設定をプロパティとして提供（J-Quants トークン、kabu API、Slack、DB パス、環境・ログレベル判定など）。
    - env と log_level の値検証（allowed list）を実装。
    - 必須環境変数未設定時にわかりやすい ValueError を投げる _require を提供。

- AI（LLM）連携
  - ニュースセンチメント解析モジュール（src/kabusys/ai/news_nlp.py）。
    - raw_news / news_symbols を集約して銘柄単位で記事をまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いて一括スコアリング。
    - バッチ処理（最大 20 銘柄/コール）、記事/文字数トリム、レスポンスバリデーション、スコアの ±1.0 クリップをサポート。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライを実装。
    - 部分失敗を想定し、ai_scores テーブルへはスコアを取得できた銘柄のみを置換（DELETE → INSERT）する安全な書き込み戦略を採用。
    - テスト容易性のため _call_openai_api の差替え（unittest.mock.patch）を想定。
  - 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news を参照して計算し、結果を market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - API エラー時は macro_sentiment = 0.0 にフォールバックするフェイルセーフ。
    - OpenAI 呼び出しは独立実装とし、モジュール間の無用な結合を避ける設計。

- データプラットフォーム（DuckDB ベース）
  - ETL パイプラインおよび結果クラス（src/kabusys/data/pipeline.py, etl.py）。
    - 差分取得、バックフィル、品質チェックの設計方針と ETLResult データクラスを実装。
    - DuckDB の挙動に配慮したテーブル存在チェックや max date 取得ユーティリティを用意。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）。
    - market_calendar テーブルを基にした営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - calendar_update_job により J-Quants からの差分フェッチと冪等保存を実施するジョブを提供（バックフィル・健全性チェック含む）。
    - カレンダーデータ未取得時は曜日（平日）をフォールバックする堅牢な挙動。

- リサーチ／ファクター計算（src/kabusys/research）
  - factor_research.py: Momentum / Volatility / Value / Liquidity 系ファクター計算を実装（prices_daily / raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離など。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率など。
    - calc_value: PER、ROE（raw_financials から最新報告）を計算。
  - feature_exploration.py: 将来リターン計算（calc_forward_returns）、IC（Spearman）計算、ランク変換、統計サマリーを提供。
    - 外部依存（pandas 等）を用いず標準ライブラリ + DuckDB で実装。
  - research パッケージの __all__ を適切に公開。

- その他
  - DuckDB に対する互換性ワークアラウンドを盛り込んだ設計（executemany に空リストを渡さない、日付型の扱い等）。
  - ドキュメント指向の詳細な docstring を多数追加し、設計方針・フェイルセーフ挙動をコード内に記述。

### 変更 (Changed)
- ロギング／挙動設計の明確化
  - 各モジュールでエラー時や特異ケースに対するログ出力を整備（warning/info/debug）。
  - API 呼び出しのリトライログやパース失敗時の警告を追加。

- セキュリティに配慮した環境変数読み込みの挙動
  - OS 環境変数を protected として .env.local からの上書きを制限する動作を採用（config._load_env_file）。

### 修正 (Fixed)
- .env パース精度向上
  - シングル／ダブルクォート内部のバックスラッシュエスケープを正しく解釈するように _parse_env_line を実装（コメント行の誤認やクォート切れ等に対する堅牢性向上）。
  - export プレフィックス対応を追加。

- OpenAI レスポンスパースの耐性強化
  - JSON Mode で稀に前後に余計なテキストが混在するケースを考慮し、最外の波括弧を抽出して復元するフォールバックを実装（news_nlp._validate_and_extract）。
  - API エラーに関して 5xx とそれ以外を区別し、リトライ対象／非対象を明確化（regime_detector._score_macro / news_nlp._score_chunk）。

- DB 書き込みの堅牢化
  - ai_scores / market_regime へは既存スコアを不用意に消さないよう「取得できたコードのみを置換」する処理にし、部分失敗時の保護を実施。
  - トランザクション失敗時に ROLLBACK を試み、ROLLBACK 自体の失敗もログ警告で捕捉する実装を追加。

### セキュリティ (Security)
- 環境変数の取り扱い改善により、OS 環境変数の誤上書きを防止（.env ロード時に protected set を導入）。
- OpenAI API キーの未設定時には明確な ValueError を出力して誤使用を防止。

### テスト支援 (Tests)
- OpenAI 呼び出し箇所に差替えポイント（_call_openai_api）を設け、ユニットテストで簡単にモック可能にしている（news_nlp, regime_detector）。

## 既知の制約 / 設計上の注意
- 本リリースでは datetime.today()/date.today() の直接参照を避け、外部から渡される target_date を基準に処理する設計であり、ルックアヘッドバイアスを防止している点に留意してください。
- DuckDB バージョン差異（executemany の空リスト扱い、リスト型バインドの挙動等）に対する互換性対策を盛り込んでいるが、運用環境の DuckDB バージョンによっては追加対応が必要な場合があります。
- ai モジュールは OpenAI API（gpt-4o-mini）に依存するため、利用時は適切な API キーと使用制限を確認してください。API 料金やレート制限の影響を受けます。

---

将来的なリリースでは、バックテスト / 実運用のエグゼキューション統合、より豊富なファクター群、モニタリング機能の強化、さらなる性能最適化を予定しています。