# KabuSys

KabuSys は日本株向けの自動売買システムの骨組み（スケルトン）です。  
このリポジトリは主要な機能をモジュール化したパッケージ構成を提供します（data / strategy / execution / monitoring）。実際の取引ロジックや外部 API 連携は含まれておらず、開発者が拡張して使うことを想定しています。

バージョン: 0.1.0

---

## 機能一覧（意図された機能）

現在のコードベースはパッケージの雛形です。将来的に実装する／実装すべき代表機能は以下のとおりです。

- data
  - 市場データの取得・キャッシュ（板情報・約定・OHLC 等）
  - 履歴データの保存と読み出し
- strategy
  - 売買シグナル生成ロジック（インジケーター、バックテスト用のシミュレーション等）
  - パラメータ管理・最適化支援
- execution
  - ブローカー API と接続して実際の注文発注／訂正／取消
  - 注文状態管理（約定・未約定のトラッキング）
- monitoring
  - ログ記録、異常検知、アラート送信（メール / Slack 等）
  - ダッシュボード表示や稼働状況の可視化

注: 現状は各モジュールの雛形パッケージのみが含まれています。実行可能な取引ロジックや API クライアントは含まれていません。

---

## セットアップ手順

このプロジェクトは src 配下にパッケージがある構成です。以下は開発環境での推奨セットアップ手順の一例です。

前提:
- Python 3.8 以降を推奨（プロジェクトの要件に応じて調整してください）

手順:

1. リポジトリをクローン
   ```
   git clone <リポジトリURL>
   cd <リポジトリ名>
   ```

2. 仮想環境の作成（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 依存パッケージのインストール
   - 現在 `requirements.txt` は含まれていません。必要なライブラリ（例: requests, pandas, numpy, websockets など）を開発に応じて追加してください。
   - 開発時は PYTHONPATH に `src` を追加する方法が手軽です:
     ```
     export PYTHONPATH=$(pwd)/src    # macOS / Linux
     set PYTHONPATH=%cd%\src         # Windows (cmd)
     ```
   - またはパッケージング設定（`pyproject.toml` / `setup.cfg` / `setup.py`）を作成して `pip install -e .` で編集可能インストールする方法もあります。

4. 環境変数・API キー
   - 実際のブローカー API を使う場合は各種 API キーや認証情報を環境変数や設定ファイルで管理してください。決済や証券会社の秘密情報は絶対にリポジトリに含めないでください。

---

## 使い方（導入例）

パッケージを読み込み、バージョンやモジュール一覧を確認する基本例:

```python
# 開発環境で PYTHONPATH=src を設定している前提
import kabusys

print(kabusys.__version__)   # 0.1.0
print(kabusys.__all__)       # ['data', 'strategy', 'execution', 'monitoring']
```

モジュールを拡張する際のサンプルテンプレート（雛形）:

- data/provider.py（例）
```python
class DataProvider:
    def fetch_quote(self, symbol):
        """現物の板情報や価格を取得して返す（実装例）"""
        raise NotImplementedError
```

- strategy/simple.py（例）
```python
class SimpleStrategy:
    def __init__(self, data_provider):
        self.data_provider = data_provider

    def on_new_tick(self, symbol):
        quote = self.data_provider.fetch_quote(symbol)
        # シグナル生成ロジック
        return "BUY"  # または "SELL", "HOLD"
```

- execution/broker.py（例）
```python
class BrokerExecutor:
    def place_order(self, symbol, side, quantity):
        """ブローカー API を呼んで注文を発行する（実装例）"""
        raise NotImplementedError
```

- monitoring/logger.py（例）
```python
class Monitor:
    def log(self, message):
        print(message)  # ここをファイル出力や外部サービスに差し替え
```

実際の運用では、上記クラスを実装して連携させ、ループやイベント駆動で戦略を稼働させます。バックテスト環境やサンドボックスで十分に検証したうえで実口座に接続してください。

---

## ディレクトリ構成

現在のリポジトリの主要ファイル構成は以下のとおりです。

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py          # パッケージのメタ情報（version, __all__）
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
└─ README.md
```

各サブパッケージ（data, strategy, execution, monitoring）は現在空の雛形ですが、ここにモジュール・クラスを実装してゆく想定です。

---

## 開発のヒント・注意事項

- 実際の注文を発行するコードはリスクが高いため、サンドボックスやペーパートレード環境で十分に検証してください。
- 金融商品取引に関わる法規制や証券会社の利用規約を必ず遵守してください。
- 機密情報（API キーや認証情報）は環境変数やシークレット管理サービスで管理し、リポジトリに含めないでください。
- バックテストとフォワードテスト（実運用テスト）は明確に分け、過学習に注意してください。

---

必要であれば、この README を元に各サブパッケージのテンプレート実装（ベースクラス、ユーティリティ、サンプル戦略、テストケース等）を追加する案内や、よく使う依存関係の雛形（requirements.txt / pyproject.toml）を作成します。どの部分を優先して整備したいか教えてください。