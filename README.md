# KabuSys

KabuSys は日本株向けの自動売買システムのベースとなる Python パッケージです。  
モジュール化された構成で、データ取得、売買戦略、注文実行、モニタリングの各責務を分離して実装を進めることを想定しています。

バージョン: 0.1.0

概要ドキュメント（README）は現状のパッケージ構成と使い始めるための手順、基本的な拡張方法を示します。現状のサブパッケージはプレースホルダとして存在しており、各モジュールに機能を実装していくことでシステムを完成させます。

## 機能一覧（想定/設計上の責務）
- data: 市場データの取得・整形・保存（ティック、板、約定履歴、OHLC 等）
- strategy: 売買戦略（アルゴリズム）を実装するためのインターフェースとサンプル戦略
- execution: 証券会社 API との接続や発注ロジック、注文管理（成行、指値、注文取消し など）
- monitoring: ログ・パフォーマンス計測・可視化・バックテスト実行や状況監視

注意: 現在のコードベースはパッケージ骨組みのみで、個々の機能（API の実装等）は含まれていません。実運用する場合は各モジュールに実装を追加し、API キー管理やリスク管理、レート制限対応等を行ってください。

## 前提・要件
- Python 3.8 以上を推奨
- 必要な外部ライブラリはプロジェクトに応じて追加してください（HTTP クライアント、データ処理用の pandas、バックテストライブラリなど）

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <リポジトリ URL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成・有効化
   - Unix / macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - パッケージとしてインストール（開発用）
     ```
     pip install -e .
     ```
     ※ プロジェクトに setup.py / pyproject.toml 等が必要です。パッケージ化しない場合は PYTHONPATH に `src` を追加して実行する方法もあります:
     ```
     export PYTHONPATH=$PWD/src:$PYTHONPATH   # Unix/macOS
     set PYTHONPATH=%CD%\src;%PYTHONPATH      # Windows (cmd)
     ```

4. 必要に応じて API キーや設定ファイルを準備
   - 証券会社 API を使う場合は安全にキーを管理（環境変数やシークレットストアを推奨）

## 使い方（初歩的な例）

パッケージのバージョン確認:
```python
from kabusys import __version__
print(__version__)  # -> "0.1.0"
```

各サブパッケージは責務ごとにファイルを実装していきます。例として各パッケージに実装するクラス/関数の雛形を示します（実装はユーザ側が追加してください）。

- data パッケージ例
```python
# src/kabusys/data/market.py
class MarketDataClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def fetch_ohlc(self, symbol: str, timeframe: str):
        # 実API呼び出しまたはデータ読み込み処理を実装
        raise NotImplementedError
```

- strategy パッケージ例
```python
# src/kabusys/strategy/base.py
class Strategy:
    def on_tick(self, data):
        # 毎ティックの処理（発注判断など）
        raise NotImplementedError

    def on_bar(self, ohlc):
        # バー確定時の処理
        raise NotImplementedError
```

- execution パッケージ例
```python
# src/kabusys/execution/broker.py
class Broker:
    def __init__(self, api_client):
        self.api_client = api_client

    def send_order(self, symbol, side, size, price=None):
        # 発注処理を実装
        raise NotImplementedError

    def cancel_order(self, order_id):
        # 注文取消し処理を実装
        raise NotImplementedError
```

- monitoring パッケージ例
```python
# src/kabusys/monitoring/monitor.py
class Monitor:
    def log_trade(self, trade_info):
        # トレードログ保存・出力
        pass

    def report(self):
        # パフォーマンスレポート生成
        pass
```

実際の実行フロー（概念）:
1. data で取得した市場データを strategy に渡す
2. strategy が条件を満たせば execution に発注要求を送る
3. execution が証券会社 API に発注し、結果を monitoring に通知
4. monitoring でログ・レポートを蓄積、必要なアラートを出す

## ディレクトリ構成

以下は現状のソースツリー（主要ファイル）です：

- src/
  - kabusys/
    - __init__.py               # パッケージ初期化、バージョン情報
    - data/
      - __init__.py
      # (市場データ関連モジュールを追加)
    - strategy/
      - __init__.py
      # (戦略関連モジュールを追加)
    - execution/
      - __init__.py
      # (発注 / ブローカラッパーを追加)
    - monitoring/
      - __init__.py
      # (モニタリング / ログ / レポートを追加)

現状のソースファイル（抜粋）:
- src/kabusys/__init__.py
  - docstring: "KabuSys - 日本株自動売買システム"
  - __version__ = "0.1.0"
  - __all__ = ["data", "strategy", "execution", "monitoring"]

各サブパッケージはプレースホルダとして存在します。必要なモジュールやクラスを追加して拡張してください。

## 開発・拡張の指針（推奨）
- サードパーティ API を使う場合は、API 呼び出しを薄いラッパー層（execution）にまとめる
- 戦略はステートレスに近い設計にするか、明示的なシリアライズ方法を用意する
- データの再現性を高めるためにロギングや時刻の扱いを統一する（タイムゾーン等）
- 単体テスト・統合テストを整備する（バックテスト用のモックデータ等）
- API キーや秘密情報は環境変数やシークレットマネージャで管理する

## ライセンス・貢献
- ライセンスは現状未設定です。利用や配布を行う場合はライセンスを明示してください。
- 貢献（機能追加、バグ修正、ドキュメント改善）は歓迎します。プルリクエストの際は実装単位で分け、テストを付けてください。

---

この README はプロジェクトの骨格に基づく案内です。実運用に使う場合は、証券会社 API の仕様に合わせた実装、堅牢なエラーハンドリング、資金管理・リスク管理の実装が必要です。必要であれば、各サブパッケージの具体的な実装テンプレートも作成しますので教えてください。