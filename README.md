# KabuSys

KabuSys は日本株向けの自動売買システムの骨組み（フレームワーク）です。リサーチやプロトタイピング、実運用コードのベースとして利用できるよう、データ取得・戦略（ストラテジー）・約定（実行）・監視の4つの主要コンポーネントに分離したモジュール構成を採っています。

注意: 現在のリポジトリはフレームワークのスケルトンです。各モジュール（data / strategy / execution / monitoring）は拡張して実装することを想定しています。

バージョン: 0.1.0

---

## 主な機能（予定・想定）

- データ取得層（data）
  - 市場データ・板情報・約定履歴などを取得するインターフェースを提供
- 戦略層（strategy）
  - 売買アルゴリズムをプラグイン的に実装・検証できる構造
- 約定層（execution）
  - 注文送信・注文管理・約定確認などの実行ロジックを統括
- 監視層（monitoring）
  - 注文・ポジション・リスク・ログの監視・アラートの仕組み

（現状は各モジュールがパッケージとして用意されているのみで、実際の実装はプロジェクトで追加してください）

---

## セットアップ手順

以下は開発者向けの基本的なセットアップ手順です。実プロジェクトに応じて依存パッケージや設定（API キー等）を追加してください。

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ名>
   ```

2. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 依存関係のインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 開発用に編集してパッケージをインストールする場合（プロジェクトルートに setup.py / pyproject.toml がある想定）:
     ```
     pip install -e .
     ```

4. 設定ファイル・環境変数
   - 実際にマーケットデータや注文を行う場合は、証券会社 API のキーやエンドポイントなどを環境変数や設定ファイルで用意してください。
   - （例）Kabuステーションやその他ブローカーAPIの認証情報

---

## 使い方（基本）

パッケージをインポートしてバージョンやモジュールを確認できます。

例:
```python
import kabusys

print(kabusys.__version__)  # "0.1.0"

# サブパッケージは以下の通り（拡張して使用）
import kabusys.data
import kabusys.strategy
import kabusys.execution
import kabusys.monitoring
```

各レイヤーの実装例（構造例・擬似コード）:

- strategy の例（シンプルな戦略クラス）
```python
# src/kabusys/strategy/simple.py
class Strategy:
    def __init__(self, data_provider, execution_engine):
        self.data = data_provider
        self.execution = execution_engine

    def on_tick(self, tick):
        # tick: 市場データの1つの更新
        # シグナル生成ロジックを実装
        if self._buy_condition(tick):
            self.execution.send_order(symbol=tick.symbol, side="BUY", qty=100)

    def _buy_condition(self, tick):
        # 条件を定義
        return False
```

- execution の例（注文送信の抽象）
```python
# src/kabusys/execution/engine.py
class ExecutionEngine:
    def __init__(self, api_client):
        self.api = api_client

    def send_order(self, symbol, side, qty, price=None):
        # API クライアント経由で注文を送信
        # 実装は各ブローカー（kabuステーション等）に合わせて作成
        pass
```

- data の例（データプロバイダの抽象）
```python
# src/kabusys/data/provider.py
class DataProvider:
    def subscribe(self, symbols, callback):
        # シンボルのデータ更新を監視し、callback を呼ぶ
        pass

    def get_history(self, symbol, period):
        # 過去データ取得
        pass
```

- monitoring の例（ログ・アラート）
```python
# src/kabusys/monitoring/logger.py
class Monitor:
    def log(self, message):
        print(message)

    def alert(self, level, message):
        # Slack やメールで通知する実装を追加
        pass
```

これらはあくまで設計例です。実際には非同期処理、リトライ、例外処理、取引所固有の制約（約定ルール・板の見方）などを組み込んでください。

---

## ディレクトリ構成

このリポジトリの主要ファイル構成（現状スケルトン）:

- src/
  - kabusys/
    - __init__.py          # パッケージ定義（バージョンなど）
    - data/
      - __init__.py        # データ取得関連パッケージ（拡張用）
    - strategy/
      - __init__.py        # 戦略実装パッケージ（拡張用）
    - execution/
      - __init__.py        # 注文送受信・実行ロジック（拡張用）
    - monitoring/
      - __init__.py        # 監視・ログ・アラート（拡張用）
- README.md                # （このファイル）
- setup.py / pyproject.toml（存在する場合あり）
- requirements.txt         # 依存があれば配置

ツリー（簡易表示）
```
project-root/
└─ src/
   └─ kabusys/
      ├─ __init__.py
      ├─ data/
      │  └─ __init__.py
      ├─ strategy/
      │  └─ __init__.py
      ├─ execution/
      │  └─ __init__.py
      └─ monitoring/
         └─ __init__.py
```

---

## 拡張と開発のヒント

- 各パッケージはインターフェース/抽象クラスを定義して、ブローカー固有の実装を差し替えられるようにするのがお勧めです。
- テストを充実させ、シミュレーション環境で戦略を検証してから実運用に移行してください。
- ログ・監視は特に重要です。注文失敗や通信断の検知、ポジションの整合性チェックを自動化してください。
- 実運用では、レート制限・注文キャンセル・部分約定・強制決済ルール等を十分に考慮すること。

---

## ライセンス / 貢献

- ライセンスや CONTRIBUTING ガイドラインがあればプロジェクトルートに追加してください。
- バグ修正・機能追加はプルリクエストで歓迎します。変更前に Issue を立てて設計方針を相談してください。

---

この README は現状のスケルトン構造に基づく導入ドキュメントです。実装を進めるにあたって、各パッケージに具体的な API ドキュメントや使用例を追加していくことを推奨します。