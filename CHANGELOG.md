# CHANGELOG

すべての注目すべき変更を記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

継続的に変更を記録してください。  

## [Unreleased]

## [0.1.0] - 2026-04-04
初期リリース。日本株自動売買システム「KabuSys」のコア機能を収録します。以下の主要コンポーネントと設計上の要点を含みます。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で定義。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイル / 環境変数から設定を自動読み込み（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - 自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD により抑止可能。
  - .env と .env.local の優先読み込みロジック（OS 環境変数保護機能あり）。
  - .env のパース機能: export 形式対応、シングル/ダブルクォート内のエスケープ処理、コメント判定等を実装。
  - Settings クラスにより各種設定をプロパティで提供:
    - J-Quants / kabuステーション / LINE / DB パス（duckdb/sqlite）/監視閾値/PID ファイルなど。
    - 環境（development / paper_trading / live）やログレベルのバリデーション。
    - 必須環境変数未設定時の明確な例外メッセージ（_require）。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄ごとのセンチメント（ai_score）を算出。
    - チャンク（最大20銘柄）単位でバッチ送信、1銘柄あたり記事数・文字数上限でトリム。
    - リトライ・バックオフ（429, ネットワーク, タイムアウト, 5xx 対応）・レスポンスバリデーション（JSON 抽出、results 配列、有効コード／スコア型チェック）。
    - スコアの ±1.0 クリップと DuckDB への冪等書き込み（対象コードのみ DELETE → INSERT）。
    - テスト容易性: _call_openai_api の差し替え（unittest.mock.patch を想定）。
    - 時刻ウィンドウ計算関数 calc_news_window（JST ベース → UTC naive datetime を返す）。

  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定。
    - LLM（gpt-4o-mini）を用いたマクロセンチメント評価、API エラー時はフェイルセーフで macro_sentiment = 0.0。
    - ルックアヘッドバイアス防止: target_date 未満のデータのみ参照、datetime.today() を参照しない実装。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK とログ。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar テーブル操作、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day）。
    - DB データがない/不完全な場合は曜日ベースのフォールバック（休日判定は土日）を採用。
    - 夜間バッチ更新ジョブ calendar_update_job による J-Quants からの差分取得、バックフィル、健全性チェック。
  - pipeline / etl:
    - ETLResult dataclass を定義し ETL の成果（取得件数、保存件数、品質問題、エラー）を集約。
    - pipeline モジュールの ETLResult を data.etl から再エクスポート。
    - 差分更新、バックフィル、品質チェック、idempotent な保存（jquants_client.save_* を想定）をサポートするための設計。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER/ROE）を DuckDB 上で計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None ハンドリング、ログ出力、営業日バッファによるスキャン範囲計算。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（情報係数）計算（calc_ic）、rank（ランク付け、同値は平均ランク）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず純 Python + DuckDB SQL で実装。
  - research パッケージは data.stats の zscore_normalize を再利用・公開。

### 設計上の注記（ドキュメント的特徴）
- ルックアヘッドバイアス対策:
  - AI モジュール・リサーチモジュールでは datetime.today() / date.today() を業務ロジックで直接参照せず、必ず target_date 引数を用いて判定/計算を行います。
- DB 操作の冪等性:
  - ETL・AI スコア保存・カレンダー更新はいずれも既存データ保護や部分失敗時の影響最小化を考慮した DELETE→INSERT／ON CONFLICT ロジックを採用。
- エラー耐性:
  - OpenAI API 呼び出しに対しリトライ（指数バックオフ）・ステータスコード判定・フェイルセーフ（0.0 やスキップ）を実装し、API 側の一時障害に対する堅牢性を確保。
- テストのしやすさ:
  - _call_openai_api の差し替えを想定した構造や環境変数自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）など、ユニットテスト用のフックを用意。
- 環境変数パースの堅牢化:
  - .env のクォート内エスケープやコメント処理、export プレフィックス対応など実運用での .env の多様な書式に対応。

### 既知の制限 / 今後の拡張候補
- 一部モジュール（jquants_client, quality モジュール等）は外部実装に依存（このリリースでは利用を前提にインターフェースを定義）。
- 現時点では PBR や配当利回りなどのバリュー指標は未実装（calc_value の注記として明示）。
- news_nlp / regime_detector ともに gpt-4o-mini を利用する想定だが、モデル変更・API 仕様変更への追従が必要。
- DuckDB バインドの互換性（executemany の空リスト制約等）を考慮した実装がなされているが、将来的に DB バージョン違いでの動作確認が必要。

### 修正・非推奨・削除
- （初期リリースのため該当なし）

### セキュリティ
- 必須 API キー（OpenAI 等）を必ず参照し、未設定時は ValueError を投げることで誤動作を防止。
- 環境変数の上書き制御（protected set）により OS 環境変数を意図せず上書きしない仕組みを導入。

---

今後のリリースでは、実運用で検出されたエッジケース対応、追加指標の実装、監視・運用（execution / monitoring）関連の機能充実を予定しています。