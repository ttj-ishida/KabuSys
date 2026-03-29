# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-29

初期リリース。日本株のデータ取得・ETL・特徴量計算・ニュースNLP・市場レジーム判定を含む自動売買基盤のコア機能を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - public API として data, research（内部モジュール経由）, ai モジュールなどをエクスポートする構成。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定自動読み込み機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml）に基づく自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
  - .env パーサ実装（コメント、export プレフィックス、シングル／ダブルクォート、エスケープ処理に対応）。
  - Settings クラスを提供（J-Quants トークン、kabu API 設定、Slack 設定、DB パス、環境判定、ログレベル等）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須変数チェック（_require）。

- AI（ニュース NLP / レジーム検出）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を元に銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（ai_score）を計算。
    - 時間ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST 相当の UTC 範囲）を提供（calc_news_window）。
    - バッチ処理（1回あたり最大 20 銘柄）、トークン肥大化対策（最大記事数・最大文字数）を実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）を指数バックオフで実装。
    - レスポンス検証ロジック（JSON 抽出、results フィールド検査、コード・スコア検証）を実装。
    - DuckDB へ冪等的に書き込むロジック（該当コードのみ DELETE → INSERT）を実装。
    - テスト性を考慮した _call_openai_api の差し替え可能設計。
  - kabusys.ai.regime_detector
    - ETF 1321（225 連動型）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily / raw_news / market_regime テーブルを参照し、DuckDB へ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - マクロ記事抽出のキーワード集合・最大記事数制限、OpenAI 呼び出しの再試行ポリシーを実装。
    - API失敗時のフェイルセーフ（macro_sentiment = 0.0）や、ルックアヘッドバイアス回避（target_date 未満のデータのみ利用）を設計要件とした実装。

- データ基盤（kabusys.data）
  - calendar_management
    - market_calendar を利用した営業日判定ユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にカレンダーがない場合の曜日ベースのフォールバック、DB 登録値優先の一貫した挙動。
    - 夜間バッチ更新ジョブ（calendar_update_job）を実装（J-Quants クライアント経由で差分取得・保存、バックフィル、健全性チェック）。
  - pipeline / ETL
    - ETLResult データクラスを公開（ETL 実行結果の集約: 取得数/保存数/品質問題/エラー等）。
    - ETL パイプラインのユーティリティ（差分更新、バックフィル、品質チェック連携）設計に沿った helper 関数を実装。
    - DuckDB のテーブル存在チェック・最大日付取得ユーティリティなどを実装。
  - jquants_client を想定した差分取得・保存ロジックのフック（実装ファイルは別途想定）。

- リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER、ROE）等のファクター計算を実装。
    - DuckDB を利用した SQL ベースの実装。データ不足時は None を返す等の堅牢な挙動。
  - feature_exploration
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ρ）計算、ランク付けユーティリティ、ファクター統計サマリーを実装。
    - pandas 等に依存しない標準ライブラリベースの実装。

- テスト性・運用に関する設計上の配慮
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接用いない設計（関数引数で基準日を与える）。
  - OpenAI 呼び出しはモジュール内部で差し替え可能（unit test 用の patch を想定）。
  - DuckDB に関する互換性注意（executemany に空リスト不可等）を考慮した実装。
  - DB 書き込みは冪等性を意識（該当日／該当コード単位で DELETE → INSERT、トランザクションハンドリング）。

### 変更 (Changed)
- 該当なし（初期リリース）

### 修正 (Fixed)
- 該当なし（初期リリース）

### 非推奨 (Deprecated)
- 該当なし（初期リリース）

### 削除 (Removed)
- 該当なし（初期リリース）

### セキュリティ (Security)
- 該当なし（初期リリース）

---

注意事項 / 既知の制約
- OpenAI API の利用には環境変数 OPENAI_API_KEY（または api_key 引数）必須。news_nlp/regime_detector はツール非依存で API 利用を試行します。
- Settings で必須となる環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用）
- 一部コンポーネント（例: jquants_client 実装、strategy/execution/monitoring の詳細実装）はこのリリースでのインターフェース／想定を含むが、実際の外部 API 実装や発注ロジックは別モジュールで提供する想定です。
- DuckDB のバージョン依存の挙動に注意（executemany 等）。運用時に使用する DuckDB バージョンで軽く動作確認を推奨します。

(本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして使用する場合はリリース担当者の確認を行ってください。)