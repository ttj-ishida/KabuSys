# Changelog

すべての非互換な変更はメジャー番号を増やすまで記載しません。  
この文書は Keep a Changelog の形式に従います。  

※以下は提供されたソースコードから推測して生成した変更履歴です。

## [Unreleased]

### 追加
- パッケージ初期構成を追加
  - パッケージルート: kabusys（__version__ = 0.1.0）
  - サブパッケージ: data, research, ai, execution, strategy, monitoring（__all__ 経由で公開）

- 設定 / 環境変数管理機能を追加（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロードを実装
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を基準）
  - .env と .env.local の読み込み順序を実装（OS環境変数を保護して .env.local を上書き）
  - export KEY=val、シングル/ダブルクォート内のバックスラッシュエスケープ、コメント処理などを含む堅牢な .env パーサを実装
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用途）
  - 必須変数取得時に未設定なら ValueError を送出するヘルパー _require を提供
  - 設定オブジェクト Settings を提供（J-Quants / kabu API / Slack / データベースパス / 環境種別 / ログレベル判定など）
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL）

- ニュース NLP および LLM ベースのスコアリング（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄毎にニュースをまとめ、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを取得
  - バッチサイズ制御、1 銘柄あたりの記事数・文字数の上限（トリム）を採用
  - JSON Mode を利用した厳密なレスポンス期待（レスポンス整形/復元ロジック含む）
  - 429 / ネットワーク断 / タイムアウト / 5xx への指数バックオフとリトライ実装
  - レスポンスの厳密なバリデーションとスコアのクリッピング（±1.0）
  - 成功したコードのみ ai_scores に置換的に書き込む（部分失敗時に既存データを保護）
  - テスト容易性のため OpenAI 呼び出しを差し替えられる設計（_call_openai_api のモック可）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定
  - マクロニュースフィルタリング、OpenAI 呼び出し、スコア合成、閾値判定（BULL/BEAR）を実装
  - API 失敗時のフェイルセーフ（macro_sentiment = 0.0）
  - ルックアヘッドバイアス対策（datetime.today()/date.today() を直接参照しない、DB クエリは target_date 未満を使用）
  - 市場レジーム結果を market_regime テーブルへ冪等的に書き込む（BEGIN/DELETE/INSERT/COMMIT）

- 研究用ファクター・特徴量モジュール（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）を計算する関数を実装（DuckDB を用いた SQL ウィンドウ関数中心の実装）
    - データ不足時の None ハンドリングを考慮
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1, 5, 21]）
    - IC（Spearman ランク相関）計算、ランク変換（同位は平均ランク）
    - factor_summary：各カラムの count/mean/std/min/max/median を算出
  - 研究モジュールは外部依存（pandas 等）を避け、DuckDB と標準ライブラリのみで完結する設計

- データ基盤ユーティリティ（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理（market_calendar テーブル）と営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装
    - カレンダー未取得時の曜日ベースフォールバック、DB 登録値優先の一貫した挙動、探索上限（_MAX_SEARCH_DAYS）など安全策を実装
    - calendar_update_job: J-Quants API からカレンダーを差分取得・バックフィルし、冪等保存する夜間バッチジョブを実装
  - pipeline / etl:
    - ETLResult データクラスを実装（取得件数、保存件数、品質問題、エラー一覧などを保持）
    - 差分更新・バックフィル設計、品質チェック（quality モジュール）との連携を想定した ETL 基盤設計
    - jquants_client を利用したフェッチ / 保存フローを想定

- テスト容易性・運用性の向上
  - OpenAI 呼び出しや .env 自動ロードの無効化など、ユニットテストで差し替えや分離を行いやすい設計
  - 詳細なログ出力を随所に追加（info / warning / debug）

### 改善
- SQL クエリは lookahead/lag/lead を適切に使い、ルックアヘッドバイアスを避ける（prices_daily クエリは target_date 未満／等を明示）
- DuckDB の executemany に関する注意を考慮（空リストでの呼び出しを回避）
- OpenAI API のエラー分類（RateLimit, APIConnectionError, APITimeoutError, APIError）に応じた再試行・フォールバックを実装
- レスポンスパースでの堅牢性強化（JSON 以外の余計なテキストをトリミングして復元する処理を追加）

### 既知の動作（設計上の意図）
- LLM 呼び出しに失敗しても処理を継続し、該当箇所はスコア 0.0（またはスキップ）でフォールバックする（フェイルセーフ）
- 日付操作はすべて date / datetime オブジェクトで扱いタイムゾーンの混入を避ける
- 一部関数は外部 API（OpenAI / J-Quants）への依存があるため、テスト時は差し替えて使用することを想定

## [0.1.0] - 2026-03-26

初回公開リリース。上記 Unreleased に記載された機能群を v0.1.0 としてパッケージ化。

### 追加
- 基本パッケージ構成とバージョン情報（kabusys.__init__）
- 環境設定管理（kabusys.config）
- AI ベースニュースセンチメント（kabusys.ai.news_nlp）
- 市場レジーム判定（kabusys.ai.regime_detector）
- 研究用ファクター／特徴量モジュール（kabusys.research.*）
- データ基盤ユーティリティ（kabusys.data.*）
- ETL 結果型（kabusys.data.pipeline.ETLResult）

### 既知の制限
- OpenAI や J-Quants など外部サービスの API キーが必須（未設定時は ValueError を発生）
- DuckDB のバージョン差異（リストバインドや executemany の挙動）に注意
- 現時点で PBR・配当利回り等の一部バリューファクターは未実装

---

作成者注:
- 本 CHANGELOG は提供されたソースコードから機能・設計意図を推測して作成したものです。実際のリリースノートや運用向けドキュメントとして使用する際は、テスト結果やリリース手順、マイグレーション情報等を追記してください。