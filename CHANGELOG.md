# Changelog

すべての重要な変更は Keep a Changelog に従って記載します。  
このプロジェクトはセマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-15

### 追加
- 初回公開リリース。
- パッケージのメタ情報を追加
  - src/kabusys/__init__.py にてバージョンを `0.1.0` として定義。
  - パッケージ外部公開モジュールとして `data`, `strategy`, `execution`, `monitoring` を __all__ に設定。

- 環境変数・設定管理モジュールを追加（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - Settings が提供するプロパティ（主なもの）:
    - J-Quants API: jquants_refresh_token（必須: JQUANTS_REFRESH_TOKEN）
    - kabuステーション API: kabu_api_password（必須: KABU_API_PASSWORD）、kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - Slack: slack_bot_token（必須: SLACK_BOT_TOKEN）、slack_channel_id（必須: SLACK_CHANNEL_ID）
    - データベースパス: duckdb_path（デフォルト: data/kabusys.duckdb）、sqlite_path（デフォルト: data/monitoring.db）
    - システム設定: env（KABUSYS_ENV、デフォルト: development、許可値: development / paper_trading / live）、log_level（LOG_LEVEL、デフォルト: INFO、許可値: DEBUG / INFO / WARNING / ERROR / CRITICAL）
    - ヘルパープロパティ: is_live, is_paper, is_dev

- 自動 .env ロードの実装
  - プロジェクトルートの自動検出:
    - src/kabusys/config.py の _find_project_root() により、.git または pyproject.toml を基準にプロジェクトルートを探索（__file__ 起点の探索のため CWD に依存しない）。
    - プロジェクトルートが見つからない場合は自動ロードをスキップ。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - OS 環境変数を保護するため、読み込み時に既存の os.environ キーを protected（不変）セットとして扱う。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1（テスト等で使用可能）。

- .env パーサーの強化
  - export プレフィックス（例: export KEY=val）に対応。
  - シングル／ダブルクォートで囲まれた値のサポート。バックスラッシュによるエスケープシーケンスを適切に処理し、対応する閉じクォートまでを値として扱う（以降のインラインコメントを無視）。
  - クォートなし値のインラインコメント処理:
    - '#' が現れた場合、直前がスペースまたはタブであればそれ以降をコメントとみなす。
  - 無効行（空行、コメント行、等）は無視。
  - ファイル読み込みでのエラーは警告を出して安全にスキップ。

- .env 読み込み制御
  - _load_env_file(path, override=False, protected=frozenset()) を実装:
    - override=False の場合、未設定のキーのみ os.environ にセット。
    - override=True の場合、protected に含まれるキーを除いて上書き。

### 変更
- なし（初版のため）

### 修正
- なし（初版のため）

### 既知の制約 / 注意点
- 必須の環境変数が未設定の場合、Settings の該当プロパティアクセス時に ValueError を送出します。`.env.example` を参考に .env を作成してください（例示ファイルは本リリースに含まれていない可能性があります）。
- プロジェクトルート検出は .git または pyproject.toml の存在に依存します。パッケージ配布や特殊な配置環境では検出に失敗する可能性があり、その場合は自動での .env 読み込みをスキップします。

--- 

（将来的なリリースでは Unreleased セクションを追加し、新機能、変更、修正、破壊的変更、セキュリティ修正等を明記します。）