# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

全般方針:
- バージョンは semver に従うものとします。
- date はリリース日を示します。

## [Unreleased]

---

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。以下の主要コンポーネントと機能が含まれます。

### Added
- パッケージ基礎
  - kabusys パッケージ（__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ として公開。

- 環境設定（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動ロードロジック:
    - プロジェクトルートの自動検出（.git または pyproject.toml を起点）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS 側に既に存在するキーは保護（protected）して上書きされない実装。
  - 高度な .env パーサー:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ対応。
    - 行内コメントの扱い（スペース等に依存するルール）。
  - Settings による厳密な検証/既定値:
    - 必須環境変数取得ヘルパー _require（未設定時は ValueError）。
    - KABUSYS_ENV の検証（development / paper_trading / live）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - 各種設定プロパティ（J-Quants, kabu API, Slack, DB パス等）。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を元にニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を提供。
    - チャンク処理（最大 20 銘柄 / 回）、記事トリム（記事数・文字数制限）によるトークン膨張対策。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - レスポンスの厳格なバリデーション（JSON 抽出・results 構造・コード照合・数値チェック）。
    - スコアは ±1.0 にクリップ。
    - 部分失敗を考慮した冪等的な DB 更新（対象コードのみ DELETE → INSERT）。
    - テスト容易性のため内部 OpenAI 呼び出し関数を差し替え可能（unittest.mock.patch で置換）。

  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込み。
    - MA 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロニュースは news_nlp.calc_news_window を利用して抽出、LLM による -1.0〜1.0 評価を JSON で取得。
    - API フェイル時のフェイルセーフ（macro_sentiment = 0.0）やリトライ・ロギングを実装。
    - レジームスコア合成と閾値によるラベリング、DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- データプラットフォーム（kabusys.data）
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar テーブル）と夜間バッチ更新ジョブ calendar_update_job を実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定ユーティリティ。
    - DB にデータがない/未登録日の場合は曜日ベースのフォールバック（土日は非営業日扱い）。
    - 最大探索日数・バックフィル・健全性チェックなど安全対策を実装。
  - pipeline:
    - ETLResult データクラス（ETL 実行結果の構造化）。
    - 差分取得・バックフィル・品質チェック（quality モジュール連携）に基づく ETL 設計方針を反映。
    - DuckDB のテーブル存在確認、最大日付取得などのユーティリティ関数。
  - etl モジュールで ETLResult を再エクスポート（kabusys.data.ETLResult）。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン, 200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金・出来高比率）、Value（PER, ROE）を DuckDB クエリベースで計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時の None 処理や、スキャン範囲のバッファ設計（カレンダー日を吸収）を行う。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns, flexible horizons）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンのランク相関）。
    - ランク変換ユーティリティ rank（同順位は平均ランク）。
    - ファクター統計サマリー関数 factor_summary（count/mean/std/min/max/median）。
  - research パッケージの __all__ に主要関数を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- API キーは関数引数で注入可能（api_key 引数）かつ環境変数 OPENAI_API_KEY を参照。API キー未設定時は明示的に ValueError を発生させることで誤用を防止。

### Notes / 実装上の設計・運用メモ
- ルックアヘッドバイアス対策:
  - 全ての関数で datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計になっています。
- テスト容易性:
  - 内部で OpenAI を呼ぶ箇所は個別のラッパー関数を用意しており、テスト時に patch で差し替え可能です。
- DuckDB の互換性対策:
  - executemany に空リストを渡せない問題に対応するため、実行前に params の空チェックを行っています。
- .env パーサーはシェルライクな書式に寄せていますが、極端なケースでは挙動が異なる可能性があります。.env.example を参考にしてください。

### Breaking Changes
- 初回リリースのため破壊的変更はありません。

---

Contributors:
- 実装内容はコードベースに基づいて推測して記載しています。今後のリリースでは各モジュールごとの細かな変更履歴（小さなバグ修正や内部 API の変更等）を個別コミットに基づいて詳細に記録してください。