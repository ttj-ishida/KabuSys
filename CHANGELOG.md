# Changelog

すべての変更は Keep a Changelog の仕様に従います。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]
- 開発中の変更点はここに記載します。

## [0.1.0] - 2026-04-02
初期リリース。日本株自動売買システムのコアライブラリを実装しました。主な追加機能・設計方針は以下のとおりです。

### Added
- パッケージ基盤
  - kabusys パッケージの初期モジュール群を追加（data, research, ai, config, etc.）。
  - バージョン情報: __version__ = "0.1.0"。

- 環境設定 / .env 読み込み（kabusys.config）
  - プロジェクトルートの自動判定（.git または pyproject.toml を探索）に基づく .env/.env.local の自動読み込みを実装。
  - .env パーサ実装: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント判定を考慮。
  - OS 環境変数を保護する protected オプション（.env.local は override=True）を実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - Settings クラスを追加し、J-Quants / kabuステーション / Slack / DB パス /監視閾値 / 環境名・ログレベル等のプロパティを提供。必須環境変数は _require() で明示的に検査。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント解析（news_nlp）
    - raw_news と news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini）へバッチで送信して ai_scores テーブルへ書き込むフローを実装。
    - バッチサイズ、銘柄ごとの最大記事数・最大文字数、JSON Mode を用いたレスポンス検証、レスポンスの堅牢なパース（余分なテキストから最外殻の JSON を抽出する復元処理）を実装。
    - API エラー（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフリトライを実装。その他エラーはスキップしてフェイルセーフ。
    - スコアは ±1.0 にクリップ。DuckDB の executemany に対する空リスト保護（事前チェック）を実装。
    - JST に基づくニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を提供（calc_news_window）。

  - 市場レジーム判定（regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - MA 計算は target_date 未満のデータのみ使用しルックアヘッドバイアスを排除。
    - マクロニュースは raw_news からマクロキーワードでフィルタし、OpenAI により JSON レスポンスで macro_sentiment を取得（API 失敗時は 0.0 で継続）。
    - レジームスコア合成と閾値によるラベル化、および market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出しのリトライや 5xx 判定処理を実装。OpenAI クライアント作成時に api_key を引数で注入可能。

- Data モジュール（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルの有無に応じた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを行い、DB がまばらでも一貫した結果を返す設計。
    - カレンダー夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント（jquants_client）経由で差分取得して保存（バックフィル、健全性チェック含む）。
    - 最大探索日数制限、バックフィル日数、先読み日数などの保護パラメータを設定。

  - ETL パイプライン（pipeline）
    - ETLResult dataclass による ETL 実行結果の集約（取得数・保存数・品質問題・エラー等）。
    - 差分更新、バックフィル、idempotent 保存（jquants_client の save_* を想定）、品質チェック（quality モジュール）との連携方針を実装。
    - テーブル存在チェック、最大日付取得等のユーティリティを用意。

- Research モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR、ATR 比率）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB SQL で計算する関数を実装。
    - データ不足時の None ハンドリング、ログ出力、結果を辞書リストで返す API を提供。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンの先の終値を LEAD で取得してリターンを計算。horizons のバリデーションを実装。
    - IC（Information Coefficient）計算（calc_ic）: ファクター値と将来リターンのスピアマンランク相関を実装（結合・欠損除外・最小レコード数チェック）。
    - ランク変換ユーティリティ（rank）とファクター統計サマリ（factor_summary）を実装。外部ライブラリに依存せず標準ライブラリのみで実装。

### Changed
- なし（初期リリース）

### Fixed
- DuckDB executemany の仕様に配慮して、空パラメータリストを渡さないよう事前チェックを追加（news_nlp / ai_scores 書き込みの互換性確保）。
- OpenAI レスポンスのパース耐性を強化（余計なテキスト混入時に最外の JSON を抽出して復元）。

### Security
- 環境変数の読み込み時に OS の既存環境変数を上書きしないデフォルト挙動（.env は override=False、.env.local は override=True だが protected により既存 OS キーは上書き防止）を採用し、重要なシークレットが意図せず上書きされるリスクを低減。

### Notes / Design decisions
- ルックアヘッドバイアス対策として、全ての時系列処理で datetime.today() / date.today() を直接参照せず、呼び出し側から target_date を明示的に受け取る設計を採用。
- OpenAI 呼び出しは API キーを引数注入可能にし、内部の _call_openai_api をテスト用にモックできるように設計（ユニットテスト容易性を重視）。
- LLM 結果は外部 API の不安定性を考慮してフェイルセーフ（失敗時は中立値 0.0 を使用、部分失敗時は他のデータを保護）を基本方針とする。
- DuckDB をデータ処理の中核に使用。SQL とウィンドウ関数を多用してパフォーマンスと可読性を両立。

### Known limitations / TODO
- 一部参照されるモジュール（例: kabusys.data.jquants_client, kabusys.data.quality, monitoring など）の実装はこのリリース内で参照されているが、ここに含まれていない可能性があります。テストや本番運用時は依存モジュールの存在を確認してください。
- 注文実行 / モニタリング（execution / monitoring）関連の実装は本スナップショットでは限定的または未実装の可能性あり。
- PBR・配当利回り等のバリューファクターは未実装（将来追加予定）。

---

過去のバージョン履歴はありません（初回リリース）。今後のリリースでは後方互換性・API 変更点を明示していきます。