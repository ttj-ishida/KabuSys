# CHANGELOG

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」形式に準拠します。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-31

初回リリース（推測）。以下はコードベースから推測してまとめた主要な追加機能・設計方針・注意点です。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期公開。バージョンは `__version__ = "0.1.0"`。
  - 公開サブパッケージ: data, research, ai, monitoring, strategy, execution（__all__ に基づく）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動探索（CWD に依存しない）。
  - .env のパースは次をサポート:
    - コメント行・空行の無視、`export KEY=val` 形式、シングル/ダブルクォート内のエスケープ処理。
    - クォート無しの値のインラインコメント扱い（直前が空白/タブの場合）。
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - Settings クラスを提供し、J-Quants・kabu API・Slack・DB パス・実行環境などをプロパティ経由で取得（未設定時は ValueError を発生させる必須チェックを実装）。
  - 環境変数のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値固定）。

- AI モジュール (src/kabusys/ai/)
  - ニュースセンチメントスコアリング (news_nlp.py)
    - raw_news + news_symbols を集約して銘柄ごとのニュースを OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み。
    - タイムウィンドウの計算（JST 基準: 前日 15:00 〜 当日 08:30）と DuckDB ベースの集約処理を実装。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの記事トリム（最大記事数・文字数制限）。
    - API 呼び出しのリトライ（レート制限、ネットワーク切断、タイムアウト、5xx）を指数バックオフで実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、コード照合、数値チェック、スコアクリップ ±1.0）。
    - 部分成功に備え、更新は対象コードのみ DELETE → INSERT を行うことで既存データ保護。
    - テスト容易性: _call_openai_api をパッチで差し替え可能。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321（Nikkei 225 連動型 ETF）の 200 日移動平均乖離（70% 重み）と、マクロニュースの LLM センチメント（30% 重み）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照し、計算されたスコアを market_regime テーブルへ冪等的に書き込み。
    - LLM 呼び出しのリトライ/フォールバック（API 失敗時は macro_sentiment=0.0）。
    - API クライアントは OpenAI SDK を使用（デフォルトモデル gpt-4o-mini）。テスト用の差し替え可能実装あり。
    - ルックアヘッドバイアス防止（target_date 未満のデータのみ使用、datetime.today を読まない設計）。

- データ・ETL・カレンダー (src/kabusys/data/)
  - ETL パイプラインインターフェース（pipeline.py / etl.py）
    - ETLResult dataclass を公開（取得件数、保存件数、品質チェック結果、エラーの集約）。
    - 差分更新、バックフィル、品質チェック、idempotent な保存（jquants_client の save_* を想定）を行う設計方針を実装。
    - DuckDB を利用した最大日付取得やテーブル存在チェック等のユーティリティ。
  - マーケットカレンダー管理（calendar_management.py）
    - market_calendar テーブルを元に営業日判定・次営業日/前営業日の取得・期間内営業日の列挙・SQ 日判定を実装。
    - DB にデータがない/未登録の日は曜日ベース（週末）でフォールバックする一貫した挙動。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・保存処理を実装。健全性チェック（将来日が過度に大きい場合はスキップ）を導入。
    - 最大探索日数制限を設け無限ループを防止。

- Research（因子・特徴量探索） (src/kabusys/research/)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR、相対 ATR、流動性指標）、Value（PER, ROE）等の計算関数を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用し、営業日ベースの窓処理を行う。
    - データ不足時は None を返す挙動。
  - feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン、ホライズン検証あり）。
    - IC（Information Coefficient）計算（Spearman のランク相関）や rank、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリで完結する実装。

- ロギング & フェイルセーフ
  - 各モジュールで詳細な logger 出力を追加（info/debug/warning）。DB 書込み失敗時は適切なロールバック処理が実装されている。
  - OpenAI 呼び出し失敗時やパース失敗時に例外を上位へ波及させない（0.0 にフォールバックやスキップ）などのフェイルセーフ設計を採用。

### 変更 (Changed)
- 初回リリースのため該当項目なし（初期実装としてまとめられている）。

### 修正 (Fixed)
- 初回リリースのため該当項目なし（実装は堅牢化を意図したハンドリング多数を含む）。

### 注意事項 / 既知の設計上の重要点
- OpenAI API キー（OPENAI_API_KEY）は news_nlp.score_news / regime_detector.score_regime の呼び出し時に必須。api_key 引数で注入可能（テスト用）。
- .env 自動読み込みはパッケージ初期化時に実行される。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して無効化推奨。
- DuckDB バージョン差異への互換性考慮（executemany の空リスト回避、リスト型バインドの回避等）を実装済み。
- AI のモデルは gpt-4o-mini に設定されているが、将来的にモデル変更の可能性あり。レスポンスの JSON モードに依存しているため、OpenAI SDK やレスポンス仕様の変更に注意。
- ルックアヘッドバイアス回避のため、日付依存処理はすべて target_date ベースで実行する設計。

---

（以降のバージョンでは変更内容をバージョン別に記載してください）